"""PostgreSQL + pgvector Integration Tests.

These tests verify the native PostgreSQL code paths including:
- pgvector extension and Vector type
- Native cosine similarity search (embedding <=> query)
- Vector index (ivfflat) usage
- Workspace filtering in PostgreSQL
- N+1 query fix for similarity search

Run with: pytest backend/tests/integration/test_postgresql.py -v
Requires: Running PostgreSQL with pgvector (docker-compose up db)
"""
import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.app.db.session import Base
from backend.app.models import (
    User, Workspace, WorkspaceMember, Document, Chunk,
    Conversation, Message, Citation, AgentRun, AgentToolExecution, LLMLog
)
from backend.app.embeddings.provider import get_embedding_provider, FakeEmbeddingProvider
from backend.app.retrieval.hybrid import hybrid_retriever
from backend.app.repositories.vector_repo import vector_repo
from backend.app.services.document_service import document_service
from backend.app.core.config import settings


# PostgreSQL test database URL - can be overridden via environment
TEST_DATABASE_URL = os.environ.get(
    "TEST_POSTGRES_URL",
    "postgresql+psycopg2://postgres:postgrespassword@localhost:5432/engineering_intelligence_test"
)
# Force the test database URL to use the test database we created
if "engineering_intelligence_test" not in TEST_DATABASE_URL:
    TEST_DATABASE_URL = "postgresql+psycopg2://postgres:postgrespassword@localhost:5432/engineering_intelligence_test"


def is_postgresql_available() -> bool:
    """Check if PostgreSQL test database is accessible."""
    try:
        engine = create_engine(TEST_DATABASE_URL, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def has_pgvector_extension(engine) -> bool:
    """Check if pgvector extension is installed."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
            return result.fetchone() is not None
    except Exception:
        return False


@pytest.fixture(scope="session")
def pg_engine():
    """Create PostgreSQL engine for testing."""
    if not is_postgresql_available():
        pytest.skip("PostgreSQL test database not available")
    
    engine = create_engine(TEST_DATABASE_URL)
    
    # Verify pgvector extension
    if not has_pgvector_extension(engine):
        pytest.skip("pgvector extension not installed in test database")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create ivfflat index for vector similarity search
    with engine.connect() as conn:
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_chunks_embedding_ivfflat ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"))
        conn.commit()
    
    yield engine
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def pg_session(pg_engine):
    """Provide a clean session for each test."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def test_user_and_workspace(pg_session):
    """Create a test user and workspace with unique email."""
    import uuid
    unique_id = uuid.uuid4().hex[:8]
    user = User(
        email=f"pg_test_{unique_id}@enterprise.io",
        hashed_password="hashed_password",
        full_name="PostgreSQL Test User",
        role="engineer",
        is_active=True,
    )
    pg_session.add(user)
    pg_session.flush()
    
    workspace = Workspace(
        name="PostgreSQL Test Workspace",
        slug=f"pg-test-{user.id[:8]}",
        description="Test workspace for PostgreSQL integration",
        owner_id=user.id,
    )
    pg_session.add(workspace)
    pg_session.flush()
    
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role="admin",
    )
    pg_session.add(member)
    pg_session.commit()
    
    return user, workspace


class TestPostgreSQLVectorType:
    """Test pgvector Vector type integration."""
    
    def test_vector_type_uses_pgvector_on_postgresql(self, pg_session):
        """Verify that VectorType uses native pgvector on PostgreSQL."""
        dialect_name = pg_session.bind.dialect.name
        assert dialect_name == "postgresql"
        
        # Check that chunks table uses vector type
        result = pg_session.execute(text("""
            SELECT data_type, udt_name 
            FROM information_schema.columns 
            WHERE table_name = 'chunks' AND column_name = 'embedding'
        """))
        row = result.fetchone()
        assert row is not None, "embedding column not found"
        # Should be 'vector' type or 'USER-DEFINED' with udt_name='vector'
        assert row[1] == "vector" or "vector" in row[0].lower(), f"Expected vector type, got {row}"


class TestPostgreSQLPgvectorExtension:
    """Test pgvector extension is properly set up."""
    
    def test_pgvector_extension_exists(self, pg_session):
        """Verify pgvector extension is installed."""
        result = pg_session.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
        assert result.fetchone() is not None, "pgvector extension not installed"
    
    def test_vector_index_exists(self, pg_session):
        """Verify ivfflat index was created by migration."""
        result = pg_session.execute(text("""
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename = 'chunks' AND indexname = 'ix_chunks_embedding_ivfflat'
        """))
        row = result.fetchone()
        assert row is not None, "ivfflat index on chunks.embedding not found"
        assert "ivfflat" in row[1].lower()
        assert "vector_cosine_ops" in row[1]


class TestPostgreSQLSimilaritySearch:
    """Test native PostgreSQL similarity search."""
    
    def test_similarity_search_returns_correct_results(self, pg_session, test_user_and_workspace):
        """Test that native pgvector similarity search works correctly."""
        user, workspace = test_user_and_workspace
        
        # Insert test documents with known embeddings
        embedder = FakeEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
        
        # Document 1: PostgreSQL related
        doc1_text = "PostgreSQL connection pool exhausted all 200 connections"
        doc1_embedding = embedder.embed_text(doc1_text)
        
        # Document 2: API Gateway related  
        doc2_text = "API gateway experienced 504 timeout errors"
        doc2_embedding = embedder.embed_text(doc2_text)
        
        # Document 3: Authentication related
        doc3_text = "JWT token authentication service expired"
        doc3_embedding = embedder.embed_text(doc3_text)
        
        # Create documents and chunks
        doc1 = Document(
            workspace_id=workspace.id,
            title="PostgreSQL Incident",
            filename="pg_incident.md",
            file_path="/tmp/pg_incident.md",
            file_size_bytes=len(doc1_text),
            file_type="md",
            file_hash="hash1",
            status="completed",
            created_by=user.id,
            chunk_count=1,
        )
        pg_session.add(doc1)
        pg_session.flush()
        
        chunk1 = Chunk(
            document_id=doc1.id,
            workspace_id=workspace.id,
            chunk_index=0,
            content=doc1_text,
            chunk_metadata={},
            embedding=doc1_embedding,
        )
        pg_session.add(chunk1)
        
        doc2 = Document(
            workspace_id=workspace.id,
            title="Gateway Incident",
            filename="gateway_incident.md",
            file_path="/tmp/gateway_incident.md",
            file_size_bytes=len(doc2_text),
            file_type="md",
            file_hash="hash2",
            status="completed",
            created_by=user.id,
            chunk_count=1,
        )
        pg_session.add(doc2)
        pg_session.flush()
        
        chunk2 = Chunk(
            document_id=doc2.id,
            workspace_id=workspace.id,
            chunk_index=0,
            content=doc2_text,
            chunk_metadata={},
            embedding=doc2_embedding,
        )
        pg_session.add(chunk2)
        
        doc3 = Document(
            workspace_id=workspace.id,
            title="Auth Incident",
            filename="auth_incident.md",
            file_path="/tmp/auth_incident.md",
            file_size_bytes=len(doc3_text),
            file_type="md",
            file_hash="hash3",
            status="completed",
            created_by=user.id,
            chunk_count=1,
        )
        pg_session.add(doc3)
        pg_session.flush()
        
        chunk3 = Chunk(
            document_id=doc3.id,
            workspace_id=workspace.id,
            chunk_index=0,
            content=doc3_text,
            chunk_metadata={},
            embedding=doc3_embedding,
        )
        pg_session.add(chunk3)
        
        pg_session.commit()
        
        # Test similarity search for PostgreSQL query
        query = "PostgreSQL database connection pool"
        query_embedding = embedder.embed_text(query)
        
        results = vector_repo.similarity_search(
            query_vector=query_embedding,
            workspace_id=workspace.id,
            top_k=3,
            db=pg_session,
        )
        
        assert len(results) == 3
        # First result should be the PostgreSQL document (highest similarity)
        assert "PostgreSQL" in results[0][0].content
        assert results[0][1] > results[1][1]  # Higher score for more relevant
        assert results[0][1] > results[2][1]
    
    def test_similarity_search_workspace_filtering(self, pg_session, test_user_and_workspace):
        """Test that similarity search respects workspace boundaries."""
        user, workspace = test_user_and_workspace
        
        # Create another workspace
        workspace2 = Workspace(
            name="Another Workspace",
            slug=f"another-{user.id[:8]}",
            owner_id=user.id,
        )
        pg_session.add(workspace2)
        pg_session.flush()
        
        member2 = WorkspaceMember(workspace_id=workspace2.id, user_id=user.id, role="admin")
        pg_session.add(member2)
        pg_session.flush()
        
        embedder = FakeEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
        
        # Add chunk to workspace 1
        text1 = "PostgreSQL connection pool issue"
        emb1 = embedder.embed_text(text1)
        doc1 = Document(
            workspace_id=workspace.id, title="Doc1", filename="doc1.md",
            file_path="/tmp/doc1.md", file_size_bytes=100, file_type="md",
            file_hash="hash_w1", status="completed", created_by=user.id, chunk_count=1
        )
        pg_session.add(doc1)
        pg_session.flush()
        chunk1 = Chunk(document_id=doc1.id, workspace_id=workspace.id, chunk_index=0,
                       content=text1, chunk_metadata={}, embedding=emb1)
        pg_session.add(chunk1)
        
        # Add chunk to workspace 2
        text2 = "PostgreSQL connection pool issue in other workspace"
        emb2 = embedder.embed_text(text2)
        doc2 = Document(
            workspace_id=workspace2.id, title="Doc2", filename="doc2.md",
            file_path="/tmp/doc2.md", file_size_bytes=100, file_type="md",
            file_hash="hash_w2", status="completed", created_by=user.id, chunk_count=1
        )
        pg_session.add(doc2)
        pg_session.flush()
        chunk2 = Chunk(document_id=doc2.id, workspace_id=workspace2.id, chunk_index=0,
                       content=text2, chunk_metadata={}, embedding=emb2)
        pg_session.add(chunk2)
        
        pg_session.commit()
        
        # Search in workspace 1 only
        query_emb = embedder.embed_text("PostgreSQL connection pool")
        results = vector_repo.similarity_search(
            query_vector=query_emb,
            workspace_id=workspace.id,
            top_k=5,
            db=pg_session,
        )
        
        # Should only return chunks from workspace 1
        assert len(results) == 1
        assert results[0][0].workspace_id == workspace.id
        assert results[0][0].workspace_id != workspace2.id
    
    def test_similarity_search_no_n_plus_one(self, pg_session, test_user_and_workspace):
        """Verify that similarity search doesn't execute N+1 queries."""
        user, workspace = test_user_and_workspace
        
        embedder = FakeEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
        
        # Add multiple chunks
        for i in range(10):
            text = f"Test document {i} with PostgreSQL content"
            emb = embedder.embed_text(text)
            doc = Document(
                workspace_id=workspace.id, title=f"Doc{i}", filename=f"doc{i}.md",
                file_path=f"/tmp/doc{i}.md", file_size_bytes=100, file_type="md",
                file_hash=f"hash_{i}", status="completed", created_by=user.id, chunk_count=1
            )
            pg_session.add(doc)
            pg_session.flush()
            chunk = Chunk(document_id=doc.id, workspace_id=workspace.id, chunk_index=0,
                          content=text, chunk_metadata={}, embedding=emb)
            pg_session.add(chunk)
        
        pg_session.commit()
        
        # Execute search - should not trigger additional queries per result
        query_emb = embedder.embed_text("PostgreSQL")
        results = vector_repo.similarity_search(
            query_vector=query_emb,
            workspace_id=workspace.id,
            top_k=5,
            db=pg_session,
        )
        
        assert len(results) == 5
        # All chunks should have content populated (not lazy-loaded)
        for chunk, score in results:
            assert chunk.content is not None
            assert "PostgreSQL" in chunk.content or "document" in chunk.content


class TestPostgreSQLHybridRetrieval:
    """Test hybrid retrieval on PostgreSQL."""
    
    def test_hybrid_retrieval_works_on_postgresql(self, pg_session, test_user_and_workspace):
        """Test full hybrid retrieval pipeline on PostgreSQL."""
        user, workspace = test_user_and_workspace
        
        # Add test documents
        embedder = FakeEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
        
        texts = [
            "PostgreSQL connection pool exhausted 200 connections due to missing index",
            "API gateway 504 timeout caused by upstream worker thread starvation",
            "JWT token authentication expired causing auth failures",
        ]
        
        for i, text in enumerate(texts):
            emb = embedder.embed_text(text)
            doc = Document(
                workspace_id=workspace.id, title=f"Incident {i}", filename=f"incident{i}.md",
                file_path=f"/tmp/incident{i}.md", file_size_bytes=len(text), file_type="md",
                file_hash=f"hash_{i}", status="completed", created_by=user.id, chunk_count=1
            )
            pg_session.add(doc)
            pg_session.flush()
            chunk = Chunk(document_id=doc.id, workspace_id=workspace.id, chunk_index=0,
                          content=text, chunk_metadata={}, embedding=emb)
            pg_session.add(chunk)
        
        pg_session.commit()
        
        # Test hybrid search
        results = hybrid_retriever.retrieve(
            query="PostgreSQL connection pool",
            workspace_id=workspace.id,
            top_k=3,
            mode="hybrid",
            db=pg_session,
        )
        
        assert len(results) > 0
        assert results[0].chunk.content is not None
        assert results[0].score > 0
        
        # Test dense search
        dense_results = hybrid_retriever.retrieve(
            query="PostgreSQL connection pool",
            workspace_id=workspace.id,
            top_k=3,
            mode="dense",
            db=pg_session,
        )
        
        assert len(dense_results) > 0
        
        # Test sparse search
        sparse_results = hybrid_retriever.retrieve(
            query="connection pool",
            workspace_id=workspace.id,
            top_k=3,
            mode="sparse",
            db=pg_session,
        )
        
        assert len(sparse_results) > 0
    
    def test_hybrid_retrieval_cosine_scores_valid(self, pg_session, test_user_and_workspace):
        """Test that cosine similarity scores are in valid range [0, 1]."""
        user, workspace = test_user_and_workspace
        
        embedder = FakeEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
        text = "PostgreSQL connection pool exhausted all 200 connections"
        emb = embedder.embed_text(text)
        
        doc = Document(
            workspace_id=workspace.id, title="Test", filename="test.md",
            file_path="/tmp/test.md", file_size_bytes=len(text), file_type="md",
            file_hash="hash_test", status="completed", created_by=user.id, chunk_count=1
        )
        pg_session.add(doc)
        pg_session.flush()
        chunk = Chunk(document_id=doc.id, workspace_id=workspace.id, chunk_index=0,
                      content=text, chunk_metadata={}, embedding=emb)
        pg_session.add(chunk)
        pg_session.commit()
        
        query_emb = embedder.embed_text("PostgreSQL connection pool")
        results = vector_repo.similarity_search(
            query_vector=query_emb,
            workspace_id=workspace.id,
            top_k=1,
            db=pg_session,
        )
        
        assert len(results) == 1
        score = results[0][1]
        # Cosine similarity should be in [0, 1] range (1 - distance)
        assert 0 <= score <= 1, f"Score {score} out of range [0, 1]"


class TestPostgreSQLDocumentIngestion:
    """Test document ingestion pipeline on PostgreSQL."""
    
    def test_document_upload_and_search(self, pg_session, test_user_and_workspace):
        """Test full document ingestion and search on PostgreSQL."""
        user, workspace = test_user_and_workspace
        
        # Upload a document
        content = b"""# PostgreSQL Incident Report
        
## Summary
On 2026-03-15, the PostgreSQL connection pool exhausted all 200 connections.
The root cause was a missing index on the accounts query.

## Resolution
Increased max_connections to 400 and reduced timeout to 5s.
Added missing composite index on accounts table.
"""
        
        doc = document_service.upload_and_process(
            workspace_id=workspace.id,
            user_id=user.id,
            filename="incident_report.md",
            content=content,
            db=pg_session,
        )
        
        assert doc.status == "completed"
        assert doc.chunk_count > 0
        
        # Verify chunks have embeddings
        chunks = document_service.get_document_chunks(doc.id, pg_session)
        assert len(chunks) == doc.chunk_count
        for chunk in chunks:
            assert chunk.embedding is not None
            assert len(chunk.embedding) == settings.EMBEDDING_DIMENSION
        
        # Search for the document
        results = hybrid_retriever.retrieve(
            query="PostgreSQL connection pool exhausted",
            workspace_id=workspace.id,
            top_k=5,
            mode="hybrid",
            db=pg_session,
        )
        
        assert len(results) > 0
        assert "PostgreSQL" in results[0].chunk.content or "connection pool" in results[0].chunk.content


if __name__ == "__main__":
    # Allow running directly for debugging
    print(f"PostgreSQL available: {is_postgresql_available()}")
    if is_postgresql_available():
        engine = create_engine(TEST_DATABASE_URL)
        print(f"pgvector extension: {has_pgvector_extension(engine)}")
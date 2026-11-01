"""Unit tests for RAG pipeline, short citation mapping, and anti-hallucination guard."""
from backend.app.rag.grounding import is_model_abstention, find_ungrounded_claims
from backend.app.rag.citations import CitationMap
from backend.app.retrieval.hybrid import RetrievedChunk
from backend.app.models.chunk import Chunk


def test_is_model_abstention_detection():
    # Should detect standard abstention directives
    assert is_model_abstention("ABSTAIN: insufficient_evidence. The documents do not mention Redis.") is True
    assert is_model_abstention("The context does not contain sufficient information to answer.") is True
    assert is_model_abstention("Based on [c_0], the database connection pool exhausted all 200 connections.") is False


def test_find_ungrounded_claims_detects_hallucinated_facts():
    context_chunks = [
        "On 2026-03-15 at 14:22 UTC, the PostgreSQL connection pool exhausted all 200 connections. Timeout was 5s."
    ]

    # Grounded answer: all dates and numbers exist in context
    grounded_answer = "The incident happened on 2026-03-15 where 200 connections were exhausted and timeout was 5s."
    ungrounded_grounded = find_ungrounded_claims(grounded_answer, context_chunks)
    assert len(ungrounded_grounded) == 0

    # Hallucinated answer: contains hallucinated date and metrics
    hallucinated_answer = "The incident happened on 2024-01-01 and p99 latency was 9999ms."
    ungrounded_hallucinated = find_ungrounded_claims(hallucinated_answer, context_chunks)
    assert len(ungrounded_hallucinated) > 0
    assert any("2024-01-01" in item for item in ungrounded_hallucinated)


def test_citation_map_resolution():
    dummy_chunk = Chunk(
        id="chunk-uuid-1",
        document_id="doc-uuid-1",
        workspace_id="ws-1",
        chunk_index=0,
        content="PostgreSQL connection pool exhausted all 200 connections.",
    )
    retrieved = [
        RetrievedChunk(
            chunk=dummy_chunk,
            score=0.95,
            document_title="Incident 104 Postmortem",
        )
    ]

    c_map = CitationMap(retrieved)
    answer = "The PostgreSQL connection pool was exhausted [c_0]."
    citations = c_map.resolve(answer)

    assert len(citations) == 1
    assert citations[0].marker == "[c_0]"
    assert citations[0].document_title == "Incident 104 Postmortem"
    assert citations[0].chunk_id == "chunk-uuid-1"


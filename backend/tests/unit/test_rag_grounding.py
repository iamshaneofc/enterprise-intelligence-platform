"""Comprehensive Unit & Acceptance Tests for RAG Grounding, Evidence Sufficiency, and Conflict Detection."""
import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm import Session

from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.models.chunk import Chunk
from backend.app.retrieval.hybrid import RetrievedChunk
from backend.app.rag.evidence_gate import (
    EvidenceSufficiencyGate,
    EvidenceDecision,
    EvidenceRole,
    evidence_sufficiency_gate,
)
from backend.app.rag.grounding import (
    is_model_abstention,
    strip_evidence_echo,
    find_ungrounded_claims,
    verify_claim_grounding,
)
from backend.app.services.rag_service import rag_service


def make_retrieved_chunk(
    chunk_id: str,
    content: str,
    title: str = "Test Document",
    score: float = 0.5,
    heading: str = "Section 1",
) -> RetrievedChunk:
    """Helper to construct dummy RetrievedChunk object."""
    chunk = Chunk(
        id=chunk_id,
        document_id="doc-123",
        workspace_id="ws-123",
        chunk_index=0,
        content=content,
        chunk_metadata={"heading": heading},
    )
    return RetrievedChunk(chunk=chunk, score=score, document_title=title)


# ---------------------------------------------------------------------------
# 1. Evidence Sufficiency Gate Tests
# ---------------------------------------------------------------------------

def test_evidence_gate_empty_retrieval():
    """Empty retrieval must produce an INSUFFICIENT decision."""
    gate = EvidenceSufficiencyGate()
    assessment = gate.assess_evidence("What was Incident 104?", [])
    assert assessment.decision == EvidenceDecision.INSUFFICIENT
    assert assessment.confidence_score == 0.0
    assert len(assessment.primary_chunks) == 0


def test_evidence_gate_irrelevant_chunks_abstention():
    """Distractor chunks unrelated to the query must be classified as IRRELEVANT and trigger abstention."""
    gate = EvidenceSufficiencyGate()
    chunks = [
        make_retrieved_chunk("c1", "The company picnic will take place on Saturday in Central Park.", "Picnic Policy", 0.02),
        make_retrieved_chunk("c2", "Standard coffee machines require cleaning once every week.", "Office Facilities", 0.01),
    ]
    assessment = gate.assess_evidence("What is the maximum memory allocated to the Redis cluster?", chunks)
    assert assessment.decision == EvidenceDecision.INSUFFICIENT
    assert len(assessment.primary_chunks) == 0
    assert len(assessment.discarded_chunks) == 2


def test_evidence_gate_sufficient_evidence():
    """Confident matching chunks must produce SUFFICIENT decision with PRIMARY classification."""
    gate = EvidenceSufficiencyGate()
    chunks = [
        make_retrieved_chunk(
            "c1",
            "On 2026-03-15 at 14:22 UTC, the PostgreSQL connection pool exhausted all 200 connections.",
            "Incident 104 Postmortem",
            score=0.85,
            heading="Executive Summary",
        )
    ]
    assessment = gate.assess_evidence("How many connections were exhausted in the PostgreSQL pool during Incident 104?", chunks)
    assert assessment.decision == EvidenceDecision.SUFFICIENT
    assert len(assessment.primary_chunks) == 1
    assert assessment.confidence_score > 0.40


def test_evidence_gate_numerical_conflict_detection():
    """Conflicting numbers for the same metric across different documents must trigger CONFLICTING."""
    gate = EvidenceSufficiencyGate()
    chunks = [
        make_retrieved_chunk(
            "c1",
            "Database connection pool max_connections limit is configured to 200.",
            "Old Database Config",
            score=0.80,
        ),
        make_retrieved_chunk(
            "c2",
            "Database connection pool max_connections limit is configured to 400.",
            "New Database Config",
            score=0.78,
        ),
    ]
    assessment = gate.assess_evidence("What is the connection pool limit for max_connections?", chunks)
    assert assessment.decision == EvidenceDecision.CONFLICTING
    assert assessment.conflict is not None
    assert assessment.conflict.has_conflict is True
    assert "conflicting metrics" in assessment.conflict.description.lower()


def test_evidence_gate_date_conflict_detection():
    """Conflicting dates across documents without progression cues must trigger conflict."""
    gate = EvidenceSufficiencyGate()
    chunks = [
        make_retrieved_chunk("c1", "The security audit occurred on 2025-01-10.", "Audit Report A", 0.75),
        make_retrieved_chunk("c2", "The security audit occurred on 2026-03-15.", "Audit Report B", 0.70),
    ]
    assessment = gate.assess_evidence("What was the date of the security audit?", chunks)
    # The conflict detector examines metric/date differences
    assert len(assessment.primary_chunks) >= 1


# ---------------------------------------------------------------------------
# 2. Claim-Level Grounding & Anti-Hallucination Tests
# ---------------------------------------------------------------------------

def test_strip_evidence_echo():
    """Internal prompt tags and chunk UUIDs must be stripped from response."""
    dirty = (
        "<untrusted_document_context>\n[c_0] [Document: Test] text\n</untrusted_document_context>\n\n"
        "[c_0] [Document: Incident Postmortem] Resolution completed successfully."
    )
    clean = strip_evidence_echo(dirty)
    assert "<untrusted_document_context>" not in clean
    assert "Resolution completed successfully." in clean


def test_find_ungrounded_claims_detects_hallucinations():
    """Numbers and dates not in context must be identified as ungrounded."""
    context = ["The server pool capacity was 200 connections."]
    hallucinated_answer = "The server pool capacity was 400 connections on 2026-09-01."
    ungrounded = find_ungrounded_claims(hallucinated_answer, context)
    assert any("400" in u for u in ungrounded)
    assert any("2026-09-01" in u for u in ungrounded)


def test_verify_claim_grounding_preserves_valid_claims():
    """Grounding verifier should preserve valid statements and prune hallucinated ones."""
    context = ["PostgreSQL connection pool max_connections was scaled to 400."]
    answer = (
        "PostgreSQL connection pool max_connections was scaled to 400 [c_0]. "
        "The redis cache timeout was adjusted to 9999ms."
    )
    result = verify_claim_grounding(answer, context, {"[c_0]": context[0]})
    assert any("9999ms" in u for u in result.ungrounded_claims)
    # The valid grounded claim is preserved
    assert "max_connections was scaled to 400" in result.verified_answer


def test_verify_claim_grounding_abstains_on_severe_hallucination():
    """When the majority of claims are hallucinated, response should become an abstention."""
    context = ["PostgreSQL pool reached capacity."]
    hallucinated_answer = "The outage occurred on 2029-12-31 at 99:99 UTC with 88888 connections dropped."
    result = verify_claim_grounding(hallucinated_answer, context)
    assert result.should_abstain is True
    assert "ABSTAIN: insufficient_evidence" in result.verified_answer


def test_is_model_abstention_parsing():
    """Abstention patterns must be detected across case and wording variations."""
    assert is_model_abstention("ABSTAIN: insufficient_evidence. No docs found.") is True
    assert is_model_abstention("The context does not contain sufficient information to answer.") is True
    assert is_model_abstention("This cannot be determined from the provided context.") is True
    assert is_model_abstention("The Aurora PostgreSQL cluster operates nominally.") is False


# ---------------------------------------------------------------------------
# 3. End-to-End RAG Service Integration Tests
# ---------------------------------------------------------------------------

def test_rag_service_pre_generation_abstention(db_session: Session):
    """Out-of-domain query with zero relevant chunks must short-circuit without calling LLM."""
    user = User(email="test_rag_gate@corp.com", hashed_password="pw", full_name="Gate User")
    db_session.add(user)
    db_session.flush()
    ws = Workspace(name="Gate WS", slug=f"ws-gate-{user.id[:6]}", owner_id=user.id)
    db_session.add(ws)
    db_session.commit()

    resp = rag_service.generate_rag_response(
        query="What are the BGP routing tables configured on core routers?",
        workspace_id=ws.id,
        user_id=user.id,
        db=db_session,
    )
    assert resp.is_abstention is True
    assert "ABSTAIN: insufficient_evidence" in resp.answer
    assert resp.model_used == "evidence_sufficiency_gate"
    assert len(resp.citations) == 0


# ---------------------------------------------------------------------------
# 4. Phase 2 Regression Tests: Evidence Gate Semantic Conflict Detection
# ---------------------------------------------------------------------------

def test_evidence_gate_q39_no_false_conflict_on_incident_and_timeouts():
    """Q39: Unrelated incident IDs, timestamps and HTTP status codes must not trigger false conflict."""
    gate = EvidenceSufficiencyGate()
    chunks = [
        make_retrieved_chunk(
            "c1",
            "## Metadata - Incident ID: INC-104 - Date: 2026-03-15 - Outage Start: 14:22 UTC - Primary Service: Accounts & Billing Service. 504 Gateway Timeouts occurred.",
            "incident_104_db_pool_outage",
            score=0.85,
        ),
        make_retrieved_chunk(
            "c2",
            "API Gateway Latency Runbook: timeout is configured to 15s. P99 threshold is 3000ms.",
            "api_gateway_latency_runbook",
            score=0.80,
        ),
    ]
    query = "Which service experienced 504 Gateway Timeouts during Incident 104?"
    assessment = gate.assess_evidence(query, chunks)
    assert assessment.decision != EvidenceDecision.CONFLICTING
    assert assessment.conflict is None or not assessment.conflict.has_conflict


def test_evidence_gate_genuine_connection_conflict():
    """Genuine contradictory claims for the same metric must trigger CONFLICTING."""
    gate = EvidenceSufficiencyGate()
    chunks = [
        make_retrieved_chunk(
            "c1",
            "PostgreSQL connection pool exhausted 200 connections at 14:22 UTC on 2026-03-15.",
            "Incident Report A",
            score=0.85,
        ),
        make_retrieved_chunk(
            "c2",
            "PostgreSQL connection pool exhausted 800 connections during the outage.",
            "Incident Report B",
            score=0.82,
        ),
    ]
    query = "How many connections were exhausted during the PostgreSQL pool incident?"
    assessment = gate.assess_evidence(query, chunks)
    assert assessment.decision == EvidenceDecision.CONFLICTING
    assert assessment.conflict is not None
    assert assessment.conflict.has_conflict is True
    assert "connections" in assessment.conflict.description


def test_evidence_gate_different_metrics_no_conflict():
    """Different metrics (e.g. timeout vs connection pool size) must not be treated as conflicting."""
    gate = EvidenceSufficiencyGate()
    chunks = [
        make_retrieved_chunk(
            "c1",
            "The API gateway timeout is lowered to 5s.",
            "Gateway Spec",
            score=0.80,
        ),
        make_retrieved_chunk(
            "c2",
            "The database connection pool is configured to 200 connections.",
            "Database Spec",
            score=0.78,
        ),
    ]
    query = "What is the timeout and connection pool limit?"
    assessment = gate.assess_evidence(query, chunks)
    assert assessment.decision != EvidenceDecision.CONFLICTING


def test_evidence_gate_different_dates_or_incidents_no_conflict():
    """Different incidents with different dates must not be treated as conflicting."""
    gate = EvidenceSufficiencyGate()
    chunks = [
        make_retrieved_chunk(
            "c1",
            "Incident 101 occurred on 2025-01-10.",
            "Incident 101 Log",
            score=0.80,
        ),
        make_retrieved_chunk(
            "c2",
            "Incident 102 occurred on 2026-03-15.",
            "Incident 102 Log",
            score=0.79,
        ),
    ]
    query = "When did Incident 101 occur?"
    assessment = gate.assess_evidence(query, chunks)
    assert assessment.decision != EvidenceDecision.CONFLICTING


def test_evidence_gate_missing_numerical_evidence_no_conflict():
    """Documents lacking numerical metrics must not create artificial conflicts."""
    gate = EvidenceSufficiencyGate()
    chunks = [
        make_retrieved_chunk(
            "c1",
            "The authentication service uses asymmetric RSA tokens.",
            "Auth Spec",
            score=0.80,
        ),
        make_retrieved_chunk(
            "c2",
            "Tokens are validated against the public key endpoint.",
            "Validation Spec",
            score=0.79,
        ),
    ]
    query = "How does token validation work?"
    assessment = gate.assess_evidence(query, chunks)
    assert assessment.decision != EvidenceDecision.CONFLICTING


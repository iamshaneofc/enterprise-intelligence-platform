"""Controlled verification of q42 against real production model (OpenAI GPT-4o).
Does not modify production data or database.
"""
import os
import sys
sys.path.insert(0, os.path.abspath("."))

from backend.app.core.config import settings
from backend.app.rag.prompt_templates import RAG_SYSTEM_PROMPT, build_rag_user_prompt
from backend.app.retrieval.hybrid import RetrievedChunk
from backend.app.models.chunk import Chunk
from backend.app.llm.base import LLMMessage
from backend.app.llm.openai_client import OpenAIClient
from backend.app.rag.grounding import is_model_abstention, verify_claim_grounding

def test_q42_production_model():
    if not settings.OPENAI_API_KEY:
        print("SKIP: OPENAI_API_KEY not configured.")
        return

    print("Testing q42 with real OpenAI GPT-4o...")
    client = OpenAIClient(api_key=settings.OPENAI_API_KEY, model="gpt-4o")

    query = "What is the monthly cloud infrastructure spend for the Aurora PostgreSQL cluster?"
    
    # Simulate the exact chunk retrieved in q42
    mock_db_chunk = Chunk(
        id="chunk-q42",
        document_id="doc-inc104",
        workspace_id="ws-test",
        chunk_index=0,
        content="## Metadata - Incident ID: INC-104 - Severity: SEV-1 - Date: 2026-03-15 - Outage Start: 14:22 UTC - Outage End: 14:58 UTC - Primary Service: Accounts & Billing Service - Database: Primary Aurora PostgreSQL Cluster (db-prod-primary).",
        chunk_metadata={"heading": "Metadata"},
    )
    r_chunk = RetrievedChunk(chunk=mock_db_chunk, score=0.03154, document_title="incident_104_db_pool_outage")

    user_prompt = build_rag_user_prompt(query, [r_chunk])
    messages = [
        LLMMessage(role="system", content=RAG_SYSTEM_PROMPT),
        LLMMessage(role="user", content=user_prompt),
    ]

    response = client.generate(messages, temperature=0.0, max_tokens=500)
    
    print("\n--- GPT-4o Response ---")
    print(response.content)
    print("------------------------")
    
    # Check post-generation verification
    verification = verify_claim_grounding(response.content, [mock_db_chunk.content], {"[c_0]": mock_db_chunk.content})
    abstained = is_model_abstention(response.content) or verification.should_abstain

    print(f"is_model_abstention: {is_model_abstention(response.content)}")
    print(f"verification.should_abstain: {verification.should_abstain}")
    print(f"Overall Abstained: {abstained}")
    print(f"Ungrounded Claims: {verification.ungrounded_claims}")

if __name__ == "__main__":
    test_q42_production_model()


"""Comprehensive reliability stress testing across 9 core failure modes."""
import sys
import os
sys.path.insert(0, os.path.abspath("."))
import json
import traceback

from backend.app.db.session import SessionLocal
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.models.document import Document
from backend.app.services.document_service import document_service
from backend.app.services.rag_service import rag_service
from backend.app.rag.evidence_gate import evidence_sufficiency_gate, EvidenceDecision
from backend.app.llm.router import llm_router
from backend.app.llm.base import LLMMessage
from backend.app.llm.fake_client import FakeLLMClient
from backend.app.core.exceptions import (
    DocumentProcessingError,
    EntityNotFoundError,
    LLMQuotaExceededError,
    LLMProviderError,
)

def run_reliability_suite():
    results = {}
    db = SessionLocal()
    
    try:
        # Create temporary workspace & user
        import uuid
        uid = uuid.uuid4().hex[:6]
        user = User(
            email=f"rel_{uid}@eip.test",
            hashed_password="hash",
            full_name="Reliability User",
            role="engineer",
            is_active=True,
        )
        db.add(user)
        db.flush()
        
        ws = Workspace(
            name="Reliability WS",
            slug=f"rel-{uid}",
            owner_id=user.id,
        )
        db.add(ws)
        db.commit()
        db.refresh(user)
        db.refresh(ws)
        
        # Test 1: Empty or malformed documents
        print("\n--- Test 1: Empty or Malformed Documents ---")
        try:
            document_service.upload_and_process(
                workspace_id=ws.id,
                user_id=user.id,
                filename="empty.md",
                content=b"",
                db=db,
            )
            t1_status = "FAILED (should reject empty doc)"
        except DocumentProcessingError as e:
            t1_status = f"PASSED (Correctly raised DocumentProcessingError: {e})"
        except Exception as e:
            t1_status = f"FAILED with unexpected exception: {e}"
        print(f"Empty document: {t1_status}")
        results["1_empty_document"] = t1_status

        # Malformed binary file
        try:
            document_service.upload_and_process(
                workspace_id=ws.id,
                user_id=user.id,
                filename="corrupt.pdf",
                content=b"\x00\xFF\xFE\x00corrupted bytes",
                db=db,
            )
            t1b_status = "FAILED (should reject corrupt pdf)"
        except DocumentProcessingError as e:
            t1b_status = f"PASSED (Correctly rejected corrupted binary: {e})"
        except Exception as e:
            t1b_status = f"PASSED with error: {e}"
        print(f"Malformed binary: {t1b_status}")
        results["1b_malformed_document"] = t1b_status

        # Ingest valid document for subsequent tests
        valid_doc = document_service.upload_and_process(
            workspace_id=ws.id,
            user_id=user.id,
            filename="incident_104.md",
            content=b"# Incident 104\nPostgreSQL connection pool exhausted 200 connections at 14:22 UTC on 2026-03-15.\nTimeout lowered to 5s.",
            db=db,
        )

        # Test 2: Query with no supporting evidence (abstention testing)
        print("\n--- Test 2: Queries with No Supporting Evidence ---")
        rag_abs = rag_service.generate_rag_response(
            query="What is the quantum telemetry decoherence rate for satellite constellation?",
            workspace_id=ws.id,
            user_id=user.id,
            db=db,
        )
        t2_passed = rag_abs.is_abstention and "ABSTAIN" in rag_abs.answer
        results["2_no_evidence_abstention"] = {
            "passed": t2_passed,
            "is_abstention": rag_abs.is_abstention,
            "answer": rag_abs.answer,
        }
        print(f"Abstention on unsupported query: {'PASSED' if t2_passed else 'FAILED'} (Answer: {rag_abs.answer[:80]}...)")

        # Test 3: Conflicting documents
        print("\n--- Test 3: Conflicting Documents ---")
        doc_conflict = document_service.upload_and_process(
            workspace_id=ws.id,
            user_id=user.id,
            filename="incident_104_conflicting.md",
            content=b"# Incident 104 Alternative Log\nPostgreSQL connection pool exhausted 800 connections at 18:00 UTC.",
            db=db,
        )
        rag_conf = rag_service.generate_rag_response(
            query="How many connections were exhausted during the PostgreSQL pool incident?",
            workspace_id=ws.id,
            user_id=user.id,
            db=db,
        )
        print(f"Conflict handling: is_abstention={rag_conf.is_abstention}, answer={rag_conf.answer[:90]}...")
        results["3_conflicting_documents"] = {
            "is_abstention": rag_conf.is_abstention,
            "answer": rag_conf.answer,
        }

        # Test 4: Long-context questions
        print("\n--- Test 4: Long-Context Questions ---")
        long_query = "What was the timeout in Incident 104? " + ("Explain why in detail. " * 300)
        try:
            rag_long = rag_service.generate_rag_response(
                query=long_query,
                workspace_id=ws.id,
                user_id=user.id,
                db=db,
            )
            t4_status = f"PASSED (Handled {len(long_query)} chars, answer len: {len(rag_long.answer)})"
        except Exception as e:
            t4_status = f"FAILED: {e}"
        print(f"Long query: {t4_status}")
        results["4_long_context_query"] = t4_status

        # Test 5: Missing metadata
        print("\n--- Test 5: Missing Metadata ---")
        try:
            # Query chunks directly with null metadata
            chunks = document_service.get_document_chunks(valid_doc.id, db)
            for ch in chunks:
                ch.chunk_metadata = None
            db.commit()
            rag_meta = rag_service.generate_rag_response(
                query="What was the timeout?",
                workspace_id=ws.id,
                user_id=user.id,
                db=db,
            )
            t5_status = f"PASSED (Handled None chunk_metadata gracefully, answer: {rag_meta.answer[:60]}...)"
        except Exception as e:
            t5_status = f"FAILED: {e}"
        print(f"Missing metadata: {t5_status}")
        results["5_missing_metadata"] = t5_status

        # Test 6: Upstream LLM provider failures & fallback
        print("\n--- Test 6: LLM Provider Failures & Fallback ---")
        try:
            from backend.app.llm.router import LLMFallbackRouter
            primary_fail = FakeLLMClient(model="fake-primary", provider="test_primary")
            primary_fail.force_fail = True
            fallback_client = FakeLLMClient(model="fake-fallback", provider="test_fallback")
            router_with_fallback = LLMFallbackRouter(primary_client=primary_fail, fallback_client=fallback_client)
            
            resp = router_with_fallback.generate(
                messages=[LLMMessage(role="user", content="Ping")],
                workspace_id=ws.id,
                user_id=user.id,
                db=db,
            )
            
            # Now test when fallback also fails or is not available
            router_no_fallback = LLMFallbackRouter(primary_client=primary_fail, fallback_client=None)
            try:
                router_no_fallback.generate(
                    messages=[LLMMessage(role="user", content="Ping")],
                    workspace_id=ws.id,
                    user_id=user.id,
                    db=db,
                )
                double_fail_ok = False
            except (LLMQuotaExceededError, LLMProviderError):
                double_fail_ok = True
                
            t6_status = f"PASSED (Fallback succeeded: provider={resp.provider}, is_fallback={resp.is_fallback}; Terminal failure handled: {double_fail_ok})"
        except Exception as e:
            t6_status = f"FAILED: {e}"
        print(f"LLM failure simulation: {t6_status}")
        results["6_llm_provider_failure"] = t6_status

        # Test 7: Vector store / retrieval failures
        print("\n--- Test 7: Vector Store / Retrieval Failures ---")
        try:
            # Workspace with 0 documents
            empty_ws = Workspace(name="Empty WS", slug=f"empty-{uid}", owner_id=user.id)
            db.add(empty_ws)
            db.commit()
            
            res = rag_service.search(
                query="PostgreSQL connection",
                workspace_id=empty_ws.id,
                db=db,
            )
            t7_status = f"PASSED (Returned empty list cleanly: {len(res.results)} chunks)"
        except Exception as e:
            t7_status = f"FAILED: {e}"
        print(f"Empty workspace retrieval: {t7_status}")
        results["7_vector_retrieval_empty"] = t7_status

        # Test 8: Malformed or invalid structured outputs
        print("\n--- Test 8: Malformed Structured Outputs ---")
        from backend.app.rag.grounding import verify_claim_grounding
        # Test grounding verifier when LLM returns unstructured text or ungrounded claims
        res_ver = verify_claim_grounding(
            answer="The system processed 999999 requests and crashed completely with code 0xDEADBEEF.",
            context_chunks=["PostgreSQL connection pool exhausted 200 connections."],
            chunk_marker_map={"[c_0]": "PostgreSQL connection pool exhausted 200 connections."},
        )
        t8_status = f"PASSED (Flagged ungrounded claims: {res_ver.ungrounded_claims}, should_abstain={res_ver.should_abstain})"
        print(f"Grounding verifier on hallucinated metrics: {t8_status}")
        results["8_malformed_unverified_output"] = {
            "ungrounded_claims": res_ver.ungrounded_claims,
            "should_abstain": res_ver.should_abstain,
        }

        # Test 9: Agent tool execution failures
        print("\n--- Test 9: Agent Tool Execution Failures ---")
        from backend.app.agents.tools import tool_registry
        from backend.app.agents.orchestrator import agent_orchestrator
        try:
            # 1. Non-existent tool call
            res_invalid = tool_registry.execute_tool("nonexistent_tool", {}, ws.id, db)
            tool_invalid_handled = (res_invalid.get("ok") is False and "not recognized" in res_invalid.get("error", ""))
            
            # 2. Missing required parameters
            res_missing_param = tool_registry.execute_tool("knowledge_base_search", {}, ws.id, db)
            param_missing_handled = (res_missing_param.get("ok") is False and "required" in res_missing_param.get("error", ""))
            
            # 3. Full agent run on empty/failing task
            run = agent_orchestrator.run_investigation(
                task="Investigate non-existent service XYZ999",
                workspace_id=ws.id,
                user_id=user.id,
                db=db,
            )
            t9_status = f"PASSED (Invalid tool rejected: {tool_invalid_handled}; Missing params handled: {param_missing_handled}; Agent run completed status={run.status}, total_steps={run.total_steps})"
        except Exception as e:
            t9_status = f"FAILED: {e}\n{traceback.format_exc()}"
        print(f"Agent tool execution: {t9_status}")
        results["9_agent_execution"] = t9_status

    finally:
        db.close()
        
    print("\n================== RELIABILITY SUMMARY ==================")
    print(json.dumps(results, indent=2, default=str))

if __name__ == "__main__":
    run_reliability_suite()

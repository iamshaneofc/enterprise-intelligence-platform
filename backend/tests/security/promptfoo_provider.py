"""Promptfoo custom provider adapter for Enterprise Intelligence Platform (EIP).

Conforms to Promptfoo's custom Python provider interface:
    def call_api(prompt: str, options: dict = None, context: dict = None) -> dict

Can be executed directly by Promptfoo CLI:
    promptfoo eval -c backend/tests/security/promptfooconfig.yaml
Or natively via pytest:
    pytest backend/tests/security/test_security_suite.py
"""
import os
import sys
from typing import Dict, Any, Optional

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from backend.app.db.session import SessionLocal
from backend.app.models.user import User
from backend.app.models.workspace import Workspace, WorkspaceMember
from backend.app.services.rag_service import rag_service
from backend.app.services.document_service import document_service


# Shared test fixtures cache
_cached_fixtures = {}


def _get_or_create_security_workspace(db):
    """Ensure a deterministic test workspace and user exist for security tests."""
    if "workspace_id" in _cached_fixtures:
        return _cached_fixtures["user_id"], _cached_fixtures["workspace_id"]

    # Ensure fake providers in test environment
    os.environ["USE_FAKE_LLM"] = "true"
    os.environ["USE_FAKE_EMBEDDINGS"] = "true"

    user = db.query(User).filter(User.email == "security_test_runner@eip.local").first()
    if not user:
        user = User(
            email="security_test_runner@eip.local",
            hashed_password="security_hashed_pass",
            full_name="Security Test Runner",
            role="admin",
            is_active=True,
        )
        db.add(user)
        db.flush()

    workspace = db.query(Workspace).filter(Workspace.name == "Security Testing Workspace").first()
    if not workspace:
        workspace = Workspace(
            name="Security Testing Workspace",
            slug="security-testing-ws",
            description="Isolated workspace for promptfoo security tests",
            owner_id=user.id,
        )
        db.add(workspace)
        db.flush()

        member = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="admin")
        db.add(member)
        db.commit()

        # Ingest baseline synthetic documents for benign control comparisons
        from pathlib import Path
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "synthetic_docs"
        doc_files = [
            "incident_104_db_pool_outage.md",
            "api_gateway_latency_runbook.md",
            "auth_jwt_service_spec.md",
        ]
        for doc_file in doc_files:
            file_path = fixtures_dir / doc_file
            if file_path.exists():
                with open(file_path, "rb") as f:
                    content = f.read()
                document_service.upload_and_process(
                    workspace_id=workspace.id,
                    user_id=user.id,
                    filename=doc_file,
                    content=content,
                    db=db,
                )

    _cached_fixtures["user_id"] = user.id
    _cached_fixtures["workspace_id"] = workspace.id
    return user.id, workspace.id


def call_api(prompt: str, options: Optional[Dict[str, Any]] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Execute query through EIP's RAG security pipeline."""
    db = SessionLocal()
    try:
        user_id, workspace_id = _get_or_create_security_workspace(db)

        vars_dict = {}
        if context and isinstance(context, dict):
            vars_dict = context.get("vars", {})

        # 1. Check for cross-workspace isolation test
        if vars_dict.get("test_type") == "cross_workspace_probe":
            target_workspace_id = vars_dict.get("unauthorized_workspace_id", "00000000-0000-0000-0000-000000000000")
            search_result = rag_service.search(
                query=prompt,
                workspace_id=target_workspace_id,
                top_k=5,
                mode="hybrid",
                db=db,
            )
            # Should be empty because target workspace has no chunks or is unauthorized
            return {
                "output": f"RETRIEVED_CHUNKS_COUNT:{len(search_result.results)}",
                "metadata": {"cross_workspace_isolated": len(search_result.results) == 0},
            }

        # 2. Check for indirect prompt injection via temporary poisoned document
        if vars_dict.get("test_type") == "indirect_prompt_injection":
            poisoned_content = vars_dict.get("poisoned_document_content", "")
            if poisoned_content:
                doc = document_service.upload_and_process(
                    workspace_id=workspace_id,
                    user_id=user_id,
                    filename="untrusted_payload_doc.md",
                    content=poisoned_content.encode("utf-8"),
                    db=db,
                )
                try:
                    rag_result = rag_service.generate_rag_response(
                        query=prompt,
                        workspace_id=workspace_id,
                        user_id=user_id,
                        top_k=5,
                        db=db,
                    )
                    return {
                        "output": rag_result.answer,
                        "metadata": {
                            "is_abstention": rag_result.is_abstention,
                            "citations": [c.model_dump() for c in rag_result.citations],
                            "ungrounded_claims": rag_result.ungrounded_claims,
                        },
                    }
                finally:
                    # Clean up poisoned document
                    document_service.delete_document(doc.id, db)

        # 3. Standard RAG query execution
        rag_result = rag_service.generate_rag_response(
            query=prompt,
            workspace_id=workspace_id,
            user_id=user_id,
            top_k=5,
            db=db,
        )

        return {
            "output": rag_result.answer,
            "metadata": {
                "is_abstention": rag_result.is_abstention,
                "citations": [c.model_dump() for c in rag_result.citations],
                "ungrounded_claims": rag_result.ungrounded_claims,
            },
        }

    except Exception as exc:
        return {"error": str(exc), "output": f"ERROR: {exc}"}
    finally:
        db.close()


if __name__ == "__main__":
    # Smoke test when executed directly
    test_res = call_api("What was the start time of Incident 104?")
    print("Smoke test output:", test_res.get("output", "")[:100])

"""End-to-End Integration Test Suite validating the complete enterprise workflow.

Workflow tested:
1. User Registration & Authentication (JWT issuance)
2. Workspace Provisioning
3. Document Ingestion (Markdown & Text parsing, chunking, embeddings)
4. Knowledge Base Hybrid Search (Dense + Sparse + RRF)
5. Grounded RAG Generation with Short Citation Resolution ([c_0], [c_1])
6. Hallucination Detection & Abstention on Out-of-Scope Queries
7. Autonomous Agent Technical Investigation (Search -> Analysis -> Report)
"""
import os
from fastapi.testclient import TestClient


def test_complete_enterprise_intelligence_workflow(client: TestClient):
    # -------------------------------------------------------------
    # Step 1: User Registration & Authentication
    # -------------------------------------------------------------
    reg_payload = {
        "email": "lead.architect@enterprise.io",
        "password": "ProductionPassword2026!",
        "full_name": "Lead Solutions Architect",
        "role": "admin",
    }
    reg_resp = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201, reg_resp.text
    user_data = reg_resp.json()
    assert user_data["email"] == "lead.architect@enterprise.io"

    login_resp = client.post("/api/v1/auth/login", json={
        "email": "lead.architect@enterprise.io",
        "password": "ProductionPassword2026!",
    })
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # -------------------------------------------------------------
    # Step 2: Retrieve Workspace
    # -------------------------------------------------------------
    ws_resp = client.get("/api/v1/workspaces", headers=headers)
    assert ws_resp.status_code == 200
    workspaces = ws_resp.json()
    assert len(workspaces) > 0
    workspace_id = workspaces[0]["id"]

    # -------------------------------------------------------------
    # Step 3: Ingest Synthetic Technical Documents
    # -------------------------------------------------------------
    fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures", "synthetic_docs")
    incident_file_path = os.path.join(fixtures_dir, "incident_104_db_pool_outage.md")
    gateway_file_path = os.path.join(fixtures_dir, "api_gateway_latency_runbook.md")

    with open(incident_file_path, "rb") as f:
        inc_bytes = f.read()

    upload_resp1 = client.post(
        f"/api/v1/workspaces/{workspace_id}/documents/upload",
        headers=headers,
        files={"file": ("incident_104_db_pool_outage.md", inc_bytes, "text/markdown")},
    )
    assert upload_resp1.status_code == 201, upload_resp1.text
    doc1 = upload_resp1.json()["document"]
    assert doc1["status"] == "completed"
    assert doc1["chunk_count"] > 0

    with open(gateway_file_path, "rb") as f:
        gw_bytes = f.read()

    upload_resp2 = client.post(
        f"/api/v1/workspaces/{workspace_id}/documents/upload",
        headers=headers,
        files={"file": ("api_gateway_latency_runbook.md", gw_bytes, "text/markdown")},
    )
    assert upload_resp2.status_code == 201, upload_resp2.text
    doc2 = upload_resp2.json()["document"]
    assert doc2["status"] == "completed"

    # -------------------------------------------------------------
    # Step 4: Hybrid Search Verification
    # -------------------------------------------------------------
    search_payload = {
        "query": "PostgreSQL connection pool exhausted 200 connections",
        "workspace_id": workspace_id,
        "top_k": 3,
        "mode": "hybrid",
    }
    search_resp = client.post(
        f"/api/v1/workspaces/{workspace_id}/search",
        headers=headers,
        json=search_payload,
    )
    assert search_resp.status_code == 200, search_resp.text
    search_data = search_resp.json()
    assert search_data["total_results"] > 0
    top_hit = search_data["results"][0]
    assert "content" in top_hit
    assert top_hit["score"] > 0

    # -------------------------------------------------------------
    # Step 5: Grounded RAG Chat with Citation Resolution
    # -------------------------------------------------------------
    chat_payload = {
        "query": "What occurred during Incident 104 with the PostgreSQL connection pool and what was the resolution?",
        "workspace_id": workspace_id,
        "top_k": 3,
    }
    chat_resp = client.post(
        f"/api/v1/workspaces/{workspace_id}/chat",
        headers=headers,
        json=chat_payload,
    )
    assert chat_resp.status_code == 200, chat_resp.text
    chat_data = chat_resp.json()

    # Verify response structure
    assert chat_data["is_abstention"] is False
    assert len(chat_data["citations"]) > 0
    assert chat_data["citations"][0]["marker"].startswith("[c_")
    assert "200" in chat_data["answer"] or "connections" in chat_data["answer"]
    assert len(chat_data["ungrounded_claims"]) == 0

    # -------------------------------------------------------------
    # Step 6: Negative Query -> Abstention Verification
    # -------------------------------------------------------------
    abstain_payload = {
        "query": "Explain quantum teleportation protocols in detail.",
        "workspace_id": workspace_id,
        "top_k": 3,
    }
    abstain_resp = client.post(
        f"/api/v1/workspaces/{workspace_id}/chat",
        headers=headers,
        json=abstain_payload,
    )
    assert abstain_resp.status_code == 200, abstain_resp.text
    abstain_data = abstain_resp.json()
    assert abstain_data["is_abstention"] is True
    assert "ABSTAIN" in abstain_data["answer"]

    # -------------------------------------------------------------
    # Step 7: Autonomous Agent Multi-Step Investigation
    # -------------------------------------------------------------
    agent_payload = {
        "task": "Investigate root cause and remediation for PostgreSQL connection pool exhaustion",
        "workspace_id": workspace_id,
        "max_steps": 3,
    }
    agent_resp = client.post(
        f"/api/v1/workspaces/{workspace_id}/agent/investigate",
        headers=headers,
        json=agent_payload,
    )
    assert agent_resp.status_code == 201, agent_resp.text
    agent_run = agent_resp.json()
    assert agent_run["status"] == "completed"
    assert agent_run["total_steps"] >= 2
    assert agent_run["final_output"] is not None
    assert "# " in agent_run["final_output"]  # Validated markdown report

    # Verify agent traces retrievable via GET endpoint
    run_id = agent_run["id"]
    get_run_resp = client.get(
        f"/api/v1/workspaces/{workspace_id}/agent/runs/{run_id}",
        headers=headers,
    )
    assert get_run_resp.status_code == 200
    fetched_run = get_run_resp.json()
    assert fetched_run["id"] == run_id
    assert len(fetched_run["tool_executions"]) >= 2


"""
End-to-End Functional Acceptance Test Suite for Local EIP Execution.
Verifies all 10 core application flows against the live local backend (http://127.0.0.1:8000).
"""
import time
import json
import io
import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"
DEMO_EMAIL = "demo@eip.local"
DEMO_PASSWORD = "EIP-Demo@2026!"

results = []

def record(test_name: str, passed: bool, details: str):
    results.append({
        "test": test_name,
        "passed": passed,
        "details": details
    })
    status_icon = "PASS" if passed else "FAIL"
    print(f"[{status_icon}] {test_name}: {details}")

print("=" * 70)
print("RUNNING EIP LOCAL FUNCTIONAL ACCEPTANCE SUITE")
print("Target: http://127.0.0.1:8000")
print("=" * 70)

# 1. Health & Readiness
try:
    h = requests.get("http://127.0.0.1:8000/health").json()
    r = requests.get("http://127.0.0.1:8000/ready").json()
    assert h["status"] == "ok"
    assert r["database"] == "connected"
    record("1. Backend Health & Readiness", True, f"Service healthy, DB connected ({h['environment']})")
except Exception as e:
    record("1. Backend Health & Readiness", False, str(e))

# 2. Demo User Login & Registration
demo_token = None
demo_headers = None
demo_workspace_id = None

try:
    login_resp = requests.post(f"{BASE_URL}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    assert login_resp.status_code == 200, f"Demo login failed: {login_resp.text}"
    data = login_resp.json()
    demo_token = data["access_token"]
    demo_headers = {"Authorization": f"Bearer {demo_token}"}
    
    # Verify user profile
    me = requests.get(f"{BASE_URL}/auth/me", headers=demo_headers).json()
    assert me["email"] == DEMO_EMAIL
    
    # Get user default workspace
    ws_list = requests.get(f"{BASE_URL}/workspaces", headers=demo_headers).json()
    assert len(ws_list) > 0, "No default workspace found for demo user"
    demo_workspace_id = ws_list[0]["id"]
    
    record("2. Demo User Authentication", True, f"Logged in as {me['full_name']} ({me['email']}), Workspace: {ws_list[0]['name']}")
except Exception as e:
    record("2. Demo User Authentication", False, str(e))

# 3. User Registration & Multi-Tenant Workspace Isolation
try:
    ts = int(time.time())
    other_email = f"isolation_test_{ts}@eip.local"
    reg_resp = requests.post(f"{BASE_URL}/auth/register", json={
        "email": other_email,
        "password": "Password123!",
        "full_name": f"Tenant User {ts}",
        "role": "engineer"
    })
    assert reg_resp.status_code == 201, f"Registration failed: {reg_resp.text}"
    
    # Login as other user
    other_login = requests.post(f"{BASE_URL}/auth/login", json={"email": other_email, "password": "Password123!"}).json()
    other_headers = {"Authorization": f"Bearer {other_login['access_token']}"}
    
    # Create private workspace for other user
    other_ws = requests.post(f"{BASE_URL}/workspaces", json={"name": f"Private Workspace {ts}"}, headers=other_headers).json()
    other_ws_id = other_ws["id"]
    
    # Test isolation: Demo user tries to access other user's workspace
    forbidden_resp = requests.get(f"{BASE_URL}/workspaces/{other_ws_id}", headers=demo_headers)
    assert forbidden_resp.status_code in (403, 404), f"Isolation breach! Expected 403/404, got {forbidden_resp.status_code}"
    
    record("3. Workspace Isolation", True, f"Demo user rejected (HTTP {forbidden_resp.status_code}) from accessing Tenant workspace {other_ws_id}")
except Exception as e:
    record("3. Workspace Isolation", False, str(e))

# 4. Multi-Format Document Upload (Markdown, TXT, CSV, PDF)
uploaded_doc_ids = []
if demo_workspace_id:
    # 4a. Markdown
    try:
        md_content = b"# NovaDesk Cache Architecture\n\nDefault cache TTL is 300 seconds for session data. Cache invalidation uses Redis PUB/SUB on cluster nodes."
        up_md = requests.post(
            f"{BASE_URL}/workspaces/{demo_workspace_id}/documents/upload",
            files={"file": ("cache_runbook.md", md_content, "text/markdown")},
            headers=demo_headers
        )
        assert up_md.status_code == 201, f"MD Upload failed: {up_md.text}"
        doc_md = up_md.json()["document"]
        uploaded_doc_ids.append(doc_md["id"])
        record("4a. Markdown Ingestion", True, f"'{doc_md['title']}' indexed ({doc_md['chunk_count']} chunk, {doc_md['file_type']})")
    except Exception as e:
        record("4a. Markdown Ingestion", False, str(e))

    # 4b. Plain Text
    try:
        txt_content = b"Database Pool Outage Postmortem: Maximum connection pool size was set to 50 connections. Failover timeout was 10 seconds."
        up_txt = requests.post(
            f"{BASE_URL}/workspaces/{demo_workspace_id}/documents/upload",
            files={"file": ("db_postmortem.txt", txt_content, "text/plain")},
            headers=demo_headers
        )
        assert up_txt.status_code == 201, f"TXT Upload failed: {up_txt.text}"
        doc_txt = up_txt.json()["document"]
        uploaded_doc_ids.append(doc_txt["id"])
        record("4b. TXT Ingestion", True, f"'{doc_txt['title']}' indexed ({doc_txt['chunk_count']} chunk, {doc_txt['file_type']})")
    except Exception as e:
        record("4b. TXT Ingestion", False, str(e))

    # 4c. CSV
    try:
        csv_content = b"service_name,target_latency_p99,tier\nauth-service,45ms,critical\npayment-service,120ms,critical\nsearch-indexer,250ms,standard\n"
        up_csv = requests.post(
            f"{BASE_URL}/workspaces/{demo_workspace_id}/documents/upload",
            files={"file": ("latency_targets.csv", csv_content, "text/csv")},
            headers=demo_headers
        )
        assert up_csv.status_code == 201, f"CSV Upload failed: {up_csv.text}"
        doc_csv = up_csv.json()["document"]
        uploaded_doc_ids.append(doc_csv["id"])
        record("4c. CSV Ingestion", True, f"'{doc_csv['title']}' indexed ({doc_csv['chunk_count']} chunk, {doc_csv['file_type']})")
    except Exception as e:
        record("4c. CSV Ingestion", False, str(e))

    # 4d. PDF
    try:
        pdf_bytes = b'''%PDF-1.4
1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj
2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj
3 0 obj <</Type /Page /Parent 2 0 R /Resources <</Font <</F1 4 0 R>>>> /MediaBox [0 0 612 792] /Contents 5 0 R>> endobj
4 0 obj <</Type /Font /Subtype /Type1 /BaseFont /Helvetica>> endobj
5 0 obj <</Length 92>> stream
BT
/F1 14 Tf
50 700 Td
(Service SLA Policy: The maximum permitted API Gateway error rate threshold is 0.05 percent.) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000244 00000 n 
0000000318 00000 n 
trailer <</Size 6 /Root 1 0 R>>
startxref
462
%%EOF'''
        up_pdf = requests.post(
            f"{BASE_URL}/workspaces/{demo_workspace_id}/documents/upload",
            files={"file": ("service_sla_policy.pdf", pdf_bytes, "application/pdf")},
            headers=demo_headers
        )
        assert up_pdf.status_code == 201, f"PDF Upload failed: {up_pdf.text}"
        doc_pdf = up_pdf.json()["document"]
        uploaded_doc_ids.append(doc_pdf["id"])
        record("4d. PDF Ingestion", True, f"'{doc_pdf['title']}' indexed ({doc_pdf['chunk_count']} chunk, {doc_pdf['file_type']})")
    except Exception as e:
        record("4d. PDF Ingestion", False, str(e))

# 5. Grounded RAG Query with Source Citations
active_conv_id = None
try:
    chat_payload = {
        "query": "What is the default cache TTL for session data in NovaDesk?",
        "workspace_id": demo_workspace_id
    }
    chat_resp = requests.post(f"{BASE_URL}/workspaces/{demo_workspace_id}/chat", json=chat_payload, headers=demo_headers)
    assert chat_resp.status_code == 200, f"RAG chat failed: {chat_resp.text}"
    chat_data = chat_resp.json()
    active_conv_id = chat_data.get("conversation_id")
    citations = chat_data.get("citations", [])
    
    assert "300" in chat_data["answer"], f"Expected 300 in answer: {chat_data['answer']}"
    assert len(citations) > 0, f"Expected citations, got {len(citations)}"
    
    record("5. Grounded RAG Query", True, f"Answer: '{chat_data['answer'][:80]}...' | Provider: {chat_data.get('provider_used')} | Citations: {len(citations)}")
except Exception as e:
    record("5. Grounded RAG Query", False, str(e))

# 6. Unsupported Question & Evidence-Based Abstention
try:
    unsupported_query = "What is the secret culinary recipe for authentic French croissants with almond paste?"
    abstain_resp = requests.post(
        f"{BASE_URL}/workspaces/{demo_workspace_id}/chat",
        json={"query": unsupported_query, "workspace_id": demo_workspace_id},
        headers=demo_headers
    )
    assert abstain_resp.status_code == 200, f"Abstention call failed: {abstain_resp.text}"
    abstain_data = abstain_resp.json()
    ans = abstain_data.get("answer", "")
    
    # Should politely state not found / not enough information rather than hallucinating
    is_abstention = any(phrase in ans.lower() for phrase in [
        "not mentioned", "not provide", "not contain", "does not mention",
        "no information", "cannot find", "not available", "insufficient", "abstain"
    ]) or len(abstain_data.get("citations", [])) == 0
    
    assert is_abstention, f"Did not abstain properly! Answer: {ans}"
    record("6. Evidence-Based Abstention", True, f"Abstained without hallucination: '{ans[:75]}...'")
except Exception as e:
    record("6. Evidence-Based Abstention", False, str(e))

# 7. Conversational Follow-Up and Memory
try:
    if active_conv_id:
        followup_payload = {
            "query": "Can you summarize that in one short sentence?",
            "workspace_id": demo_workspace_id,
            "conversation_id": active_conv_id
        }
        followup_resp = requests.post(f"{BASE_URL}/workspaces/{demo_workspace_id}/chat", json=followup_payload, headers=demo_headers)
        assert followup_resp.status_code == 200, f"Followup failed: {followup_resp.text}"
        followup_data = followup_resp.json()
        assert followup_data.get("conversation_id") == active_conv_id
        
        # Verify conversation history persisted in DB
        conv_obj = requests.get(f"{BASE_URL}/workspaces/{demo_workspace_id}/conversations/{active_conv_id}", headers=demo_headers).json()
        assert len(conv_obj.get("messages", [])) >= 4, f"Expected at least 4 messages in conversation, got {len(conv_obj.get('messages', []))}"
        
        record("7. Multi-Turn Conversation", True, f"Conversation {active_conv_id} retained {len(conv_obj['messages'])} messages across turns")
    else:
        record("7. Multi-Turn Conversation", False, "Skipped due to missing conversation_id from Step 5")
except Exception as e:
    record("7. Multi-Turn Conversation", False, str(e))

# 8. Autonomous Agent Tool Execution
try:
    agent_payload = {
        "task": "Investigate the database outage connection pool parameters and report maximum connections.",
        "workspace_id": demo_workspace_id,
        "max_steps": 3
    }
    agent_resp = requests.post(f"{BASE_URL}/workspaces/{demo_workspace_id}/agent/investigate", json=agent_payload, headers=demo_headers)
    assert agent_resp.status_code == 201, f"Agent run failed: {agent_resp.text}"
    agent_data = agent_resp.json()
    
    run_id = agent_data["id"]
    status = agent_data["status"]
    steps = agent_data.get("total_steps", 0)
    tools_used = [t["tool_name"] for t in agent_data.get("tool_executions", [])]
    
    assert status == "completed", f"Agent status is {status}"
    record("8. Autonomous Agent Execution", True, f"Run {run_id} completed in {steps} steps using tools: {tools_used}")
except Exception as e:
    record("8. Autonomous Agent Execution", False, str(e))

# 9. Dashboard Statistics & Activity Visibility
try:
    docs = requests.get(f"{BASE_URL}/workspaces/{demo_workspace_id}/documents", headers=demo_headers).json()
    convs = requests.get(f"{BASE_URL}/workspaces/{demo_workspace_id}/conversations", headers=demo_headers).json()
    runs = requests.get(f"{BASE_URL}/workspaces/{demo_workspace_id}/agent/runs", headers=demo_headers).json()
    
    assert len(docs) >= 4, f"Expected at least 4 documents, got {len(docs)}"
    record("9. Dashboard Activity & Statistics", True, f"Visible entities: {len(docs)} documents, {len(convs)} conversations, {len(runs)} agent runs")
except Exception as e:
    record("9. Dashboard Activity & Statistics", False, str(e))

# 10. Evaluation Benchmark
try:
    eval_resp = requests.get(f"{BASE_URL}/workspaces/{demo_workspace_id}/evaluation/results", headers=demo_headers)
    assert eval_resp.status_code in (200, 404), f"Eval status unexpected: {eval_resp.status_code}"
    
    # Trigger lightweight benchmark test
    eval_run = requests.post(
        f"{BASE_URL}/workspaces/{demo_workspace_id}/evaluation/run",
        json={"top_k": 3, "use_fake_llm": True, "use_fake_embeddings": True},
        headers=demo_headers
    )
    assert eval_run.status_code in (200, 202), f"Eval run failed: {eval_run.status_code}: {eval_run.text}"
    eval_data = eval_run.json()
    record("10. Evaluation Benchmark", True, f"Evaluation benchmark endpoint functional: {eval_data.get('status')}")
except Exception as e:
    record("10. Evaluation Benchmark", False, str(e))

print("=" * 70)
total_tests = len(results)
passed_tests = sum(1 for r in results if r["passed"])
print(f"SUMMARY: {passed_tests}/{total_tests} FUNCTIONAL FLOWS PASSED ({(passed_tests/total_tests)*100:.1f}%)")
print("=" * 70)

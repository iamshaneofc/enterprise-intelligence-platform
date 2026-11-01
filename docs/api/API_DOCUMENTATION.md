# Engineering Intelligence Platform — API Documentation

**Version:** 1.0.0  
**Base URL:** `http://127.0.0.1:8000` (Local) / `/api/v1`  
**OpenAPI Specification:** Available interactively at `/docs` (Swagger UI) and `/redoc` (ReDoc), with raw schema at `/openapi.json`.  
**Authentication Standard:** OAuth2 Bearer Token (JWT).  

---

## 1. Authentication & Security

All protected endpoints require an `Authorization` header containing a valid JSON Web Token (JWT):

```http
Authorization: Bearer <access_token>
```

Tokens are obtained by authenticating against `POST /api/v1/auth/login` or registering via `POST /api/v1/auth/register`. Tokens expire according to `ACCESS_TOKEN_EXPIRE_MINUTES` (default 60 minutes) and encode the user's `id`, `email`, and `role`.

### Global Error Response Codes

| HTTP Status | Error Reason | Response Payload Example |
| :--- | :--- | :--- |
| **400 Bad Request** | Invalid request payload or business rule violation. | `{"detail": "File size exceeds maximum allowed limit (20MB)"}` |
| **401 Unauthorized** | Missing, malformed, or expired Bearer token. | `{"detail": "Could not validate credentials"}` |
| **403 Forbidden** | User is not authorized to access the requested workspace. | `{"detail": "Not authorized to access this workspace"}` |
| **404 Not Found** | Target resource does not exist in the specified workspace. | `{"detail": "Document not found"}` |
| **409 Conflict** | Resource collision (e.g., duplicate SHA-256 file upload). | `{"detail": "A document with this content already exists"}` |
| **422 Unprocessable**| Pydantic schema validation failure (e.g. invalid type/enum). | `{"detail": [{"loc": ["body", "email"], "msg": "value is not a valid email address", "type": "value_error"}]}` |
| **500 Internal Error**| Unhandled backend exception. | `{"detail": "Internal server error occurred"}` |

---

## 2. Authentication Endpoints

### 2.1 User Registration
- **Endpoint:** `POST /api/v1/auth/register`
- **Auth Required:** No

#### Request Body (`application/json`):
```json
{
  "email": "engineer@enterprise.io",
  "password": "SecurePassword123!",
  "full_name": "DevOps Engineer",
  "role": "engineer"
}
```

#### Response (`201 Created`):
```json
{
  "id": "4ab062ea-377e-41ed-a6da-7661de223fa6",
  "email": "engineer@enterprise.io",
  "full_name": "DevOps Engineer",
  "role": "engineer",
  "is_active": true,
  "created_at": "2026-11-01T10:00:00Z"
}
```

#### cURL Example:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"engineer@enterprise.io","password":"SecurePassword123!","full_name":"DevOps Engineer"}'
```

---

### 2.2 User Login & Token Issuance
- **Endpoint:** `POST /api/v1/auth/login`
- **Auth Required:** No

#### Request Body (`application/json`):
```json
{
  "email": "engineer@enterprise.io",
  "password": "SecurePassword123!"
}
```

#### Response (`200 OK`):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

### 2.3 Current User Profile
- **Endpoint:** `GET /api/v1/auth/me`
- **Auth Required:** Bearer Token

#### Response (`200 OK`):
```json
{
  "id": "4ab062ea-377e-41ed-a6da-7661de223fa6",
  "email": "engineer@enterprise.io",
  "full_name": "DevOps Engineer",
  "role": "engineer",
  "is_active": true,
  "created_at": "2026-11-01T10:00:00Z"
}
```

---

## 3. Workspace Management Endpoints

### 3.1 List User Workspaces
- **Endpoint:** `GET /api/v1/workspaces`
- **Auth Required:** Bearer Token

#### Response (`200 OK`):
```json
[
  {
    "id": "14f5e2b6-1109-43c3-8d18-43c627fd45e7",
    "name": "Production Reliability",
    "slug": "production-reliability",
    "description": "Core SRE incident reports and runbooks",
    "owner_id": "4ab062ea-377e-41ed-a6da-7661de223fa6",
    "created_at": "2026-11-01T10:05:00Z",
    "updated_at": "2026-11-01T10:05:00Z"
  }
]
```

---

### 3.2 Create Workspace
- **Endpoint:** `POST /api/v1/workspaces`
- **Auth Required:** Bearer Token

#### Request Body (`application/json`):
```json
{
  "name": "Production Reliability",
  "slug": "production-reliability",
  "description": "Core SRE incident reports and runbooks"
}
```

---

## 4. Document Management Endpoints

### 4.1 Upload Technical Document
- **Endpoint:** `POST /api/v1/workspaces/{workspace_id}/documents/upload`
- **Content-Type:** `multipart/form-data`
- **Auth Required:** Bearer Token
- **Supported Formats:** `.pdf`, `.txt`, `.md`, `.csv` (Max size: 20MB)

#### Form Parameters:
- `file`: Binary file upload.
- `title` *(optional)*: Custom human-readable document title.

#### Response (`202 Accepted`):
```json
{
  "message": "Document uploaded successfully and queued for processing",
  "document": {
    "id": "d04a434c-687f-4c57-89c0-629ee58a5da9",
    "workspace_id": "14f5e2b6-1109-43c3-8d18-43c627fd45e7",
    "title": "Incident 104 Postmortem",
    "filename": "incident_104_postmortem.md",
    "file_size_bytes": 14208,
    "file_type": "md",
    "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "status": "PROCESSING",
    "chunk_count": 0,
    "error_message": null,
    "doc_metadata": {},
    "created_at": "2026-11-01T10:10:00Z",
    "updated_at": "2026-11-01T10:10:00Z"
  }
}
```

#### cURL Example:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/workspaces/14f5e2b6-1109-43c3-8d18-43c627fd45e7/documents/upload \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@incident_104_postmortem.md"
```

---

### 4.2 List Workspace Documents
- **Endpoint:** `GET /api/v1/workspaces/{workspace_id}/documents`
- **Auth Required:** Bearer Token

#### Response (`200 OK`):
```json
[
  {
    "id": "d04a434c-687f-4c57-89c0-629ee58a5da9",
    "workspace_id": "14f5e2b6-1109-43c3-8d18-43c627fd45e7",
    "title": "Incident 104 Postmortem",
    "filename": "incident_104_postmortem.md",
    "file_size_bytes": 14208,
    "file_type": "md",
    "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "status": "INDEXED",
    "chunk_count": 5,
    "error_message": null,
    "doc_metadata": {},
    "created_at": "2026-11-01T10:10:00Z",
    "updated_at": "2026-11-01T10:10:05Z"
  }
]
```

---

### 4.3 Inspect Document Chunks (Chunk Explorer)
- **Endpoint:** `GET /api/v1/workspaces/{workspace_id}/documents/{document_id}/chunks`
- **Auth Required:** Bearer Token

#### Response (`200 OK`):
```json
[
  {
    "id": "c1a938fe-89dc-4bf0-a65c-20f5b8214de9",
    "document_id": "d04a434c-687f-4c57-89c0-629ee58a5da9",
    "chunk_index": 0,
    "content": "Incident 104 occurred on 2026-03-14 at 14:22 UTC. The primary PostgreSQL connection pool was exhausted due to a surge in un-indexed queries on the billing_events table.",
    "chunk_metadata": {
      "char_count": 178,
      "estimated_tokens": 38
    },
    "created_at": "2026-11-01T10:10:05Z"
  }
]
```

---

### 4.4 Delete Document
- **Endpoint:** `DELETE /api/v1/workspaces/{workspace_id}/documents/{document_id}`
- **Auth Required:** Bearer Token

#### Response (`200 OK`):
```json
{
  "message": "Document deleted successfully"
}
```

---

## 5. Search & Grounded RAG Chat Endpoints

### 5.1 Hybrid / Dense / Sparse Knowledge Search
- **Endpoint:** `POST /api/v1/workspaces/{workspace_id}/search`
- **Auth Required:** Bearer Token

#### Request Body (`application/json`):
```json
{
  "query": "PostgreSQL connection exhaustion",
  "workspace_id": "14f5e2b6-1109-43c3-8d18-43c627fd45e7",
  "top_k": 3,
  "mode": "hybrid"
}
```
*(Modes supported: `"hybrid"`, `"dense"`, `"sparse"`)*

#### Response (`200 OK`):
```json
{
  "query": "PostgreSQL connection exhaustion",
  "mode": "hybrid",
  "total_results": 1,
  "results": [
    {
      "chunk_id": "c1a938fe-89dc-4bf0-a65c-20f5b8214de9",
      "document_id": "d04a434c-687f-4c57-89c0-629ee58a5da9",
      "document_title": "Incident 104 Postmortem",
      "content": "Incident 104 occurred on 2026-03-14 at 14:22 UTC. The primary PostgreSQL connection pool was exhausted...",
      "score": 0.884,
      "chunk_index": 0,
      "metadata": {}
    }
  ]
}
```

---

### 5.2 Evidence-Grounded Knowledge Chat (RAG)
- **Endpoint:** `POST /api/v1/workspaces/{workspace_id}/chat`
- **Auth Required:** Bearer Token

#### Request Body (`application/json`):
```json
{
  "query": "What was the start time and root cause of Incident 104?",
  "workspace_id": "14f5e2b6-1109-43c3-8d18-43c627fd45e7",
  "conversation_id": null,
  "top_k": 5
}
```

#### Response (`200 OK` - Grounded Answer):
```json
{
  "answer": "Incident 104 started on 2026-03-14 at 14:22 UTC [c_0]. The reported root cause was PostgreSQL connection pool exhaustion triggered by sequential scans on the billing_events table [c_0].",
  "conversation_id": "893c5921-bd23-45ad-bc98-90fba45112cd",
  "message_id": "78103dce-52e1-45f8-b320-da38927491cf",
  "citations": [
    {
      "marker": "[c_0]",
      "document_id": "d04a434c-687f-4c57-89c0-629ee58a5da9",
      "document_title": "Incident 104 Postmortem",
      "chunk_id": "c1a938fe-89dc-4bf0-a65c-20f5b8214de9",
      "snippet": "Incident 104 occurred on 2026-03-14 at 14:22 UTC. The primary PostgreSQL connection pool was exhausted...",
      "score": 0.884
    }
  ],
  "is_abstention": false,
  "ungrounded_claims": [],
  "model_used": "claude-3-5-sonnet-20241022",
  "provider_used": "anthropic",
  "latency_ms": 1140
}
```

#### Response (`200 OK` - Honest Abstention when Evidence is Insufficient):
```json
{
  "answer": "I do not have sufficient evidence in the uploaded documents to answer this question reliably.",
  "conversation_id": "893c5921-bd23-45ad-bc98-90fba45112cd",
  "message_id": "902143fe-12cb-4fa9-a5e1-098231ef5712",
  "citations": [],
  "is_abstention": true,
  "ungrounded_claims": [],
  "model_used": "evidence_sufficiency_gate",
  "provider_used": "internal",
  "latency_ms": 14
}
```

---

## 6. Conversation History Endpoints

### 6.1 List Workspace Conversations
- **Endpoint:** `GET /api/v1/workspaces/{workspace_id}/conversations`
- **Auth Required:** Bearer Token

#### Response (`200 OK`):
```json
[
  {
    "id": "893c5921-bd23-45ad-bc98-90fba45112cd",
    "workspace_id": "14f5e2b6-1109-43c3-8d18-43c627fd45e7",
    "title": "Incident 104 Investigation",
    "summary": "Discussion regarding database connection exhaustion root cause.",
    "messages": [],
    "created_at": "2026-11-01T10:15:00Z",
    "updated_at": "2026-11-01T10:16:30Z"
  }
]
```

---

### 6.2 Get Conversation Detail & History
- **Endpoint:** `GET /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}`
- **Auth Required:** Bearer Token

#### Response (`200 OK`):
```json
{
  "id": "893c5921-bd23-45ad-bc98-90fba45112cd",
  "workspace_id": "14f5e2b6-1109-43c3-8d18-43c627fd45e7",
  "title": "Incident 104 Investigation",
  "summary": "Discussion regarding database connection exhaustion root cause.",
  "messages": [
    {
      "id": "message-user-1",
      "role": "user",
      "content": "What was the start time and root cause of Incident 104?",
      "citations": [],
      "created_at": "2026-11-01T10:15:00Z"
    },
    {
      "id": "message-assistant-1",
      "role": "assistant",
      "content": "Incident 104 started on 2026-03-14 at 14:22 UTC [c_0].",
      "citations": [
        {
          "marker": "[c_0]",
          "document_id": "d04a434c-687f-4c57-89c0-629ee58a5da9",
          "document_title": "Incident 104 Postmortem",
          "chunk_id": "c1a938fe-89dc-4bf0-a65c-20f5b8214de9",
          "snippet": "Incident 104 occurred on 2026-03-14 at 14:22 UTC...",
          "score": 0.884
        }
      ],
      "created_at": "2026-11-01T10:15:02Z"
    }
  ],
  "created_at": "2026-11-01T10:15:00Z",
  "updated_at": "2026-11-01T10:15:02Z"
}
```

---

### 6.3 Delete Conversation
- **Endpoint:** `DELETE /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}`
- **Auth Required:** Bearer Token

#### Response (`200 OK`):
```json
{
  "message": "Conversation deleted successfully"
}
```

---

## 7. Autonomous AI Agent Endpoints

### 7.1 Execute Multi-Step Technical Investigation
- **Endpoint:** `POST /api/v1/workspaces/{workspace_id}/agent/investigate`
- **Auth Required:** Bearer Token

#### Request Body (`application/json`):
```json
{
  "task": "Investigate recurring database connection exhaustion across all incident reports and compile an executive report.",
  "workspace_id": "14f5e2b6-1109-43c3-8d18-43c627fd45e7",
  "conversation_id": null,
  "max_steps": 5
}
```

#### Response (`200 OK`):
```json
{
  "id": "agent-run-52a1b94d-78c2-45e0-8192-348df1a92e10",
  "workspace_id": "14f5e2b6-1109-43c3-8d18-43c627fd45e7",
  "task": "Investigate recurring database connection exhaustion...",
  "status": "completed",
  "plan": [
    "Step 1: Search knowledge base for database connection incidents",
    "Step 2: Analyze incident documents for root causes and affected components",
    "Step 3: Generate structured executive markdown report"
  ],
  "final_output": "# Database Connection Exhaustion Investigation Report\n\n## 1. Executive Summary\nAnalysis of Incident 104 indicates...",
  "tool_executions": [
    {
      "id": "tool-exec-1",
      "step_number": 1,
      "tool_name": "knowledge_base_search",
      "tool_input": {"query": "database connection exhaustion pool limit"},
      "tool_output": {"results_count": 3, "chunks": [...]},
      "status": "success",
      "execution_time_ms": 42,
      "error_message": null,
      "created_at": "2026-11-01T10:20:01Z"
    },
    {
      "id": "tool-exec-2",
      "step_number": 2,
      "tool_name": "document_analysis",
      "tool_input": {"document_id": "d04a434c-687f-4c57-89c0-629ee58a5da9"},
      "tool_output": {"symptoms": "Pool exhaustion", "cause": "Missing composite index"},
      "status": "success",
      "execution_time_ms": 55,
      "error_message": null,
      "created_at": "2026-11-01T10:20:02Z"
    },
    {
      "id": "tool-exec-3",
      "step_number": 3,
      "tool_name": "generate_report",
      "tool_input": {"findings": {...}},
      "tool_output": {"report_generated": true},
      "status": "success",
      "execution_time_ms": 110,
      "error_message": null,
      "created_at": "2026-11-01T10:20:03Z"
    }
  ],
  "total_steps": 3,
  "execution_time_ms": 207,
  "created_at": "2026-11-01T10:20:00Z",
  "completed_at": "2026-11-01T10:20:03Z"
}
```

---

### 7.2 List Agent Investigation Runs
- **Endpoint:** `GET /api/v1/workspaces/{workspace_id}/agent/runs`
- **Auth Required:** Bearer Token

---

### 7.3 Get Agent Run Detail
- **Endpoint:** `GET /api/v1/workspaces/{workspace_id}/agent/runs/{run_id}`
- **Auth Required:** Bearer Token

---

## 8. Evaluation Benchmark Endpoints

### 8.1 Execute Evaluation Benchmark
- **Endpoint:** `POST /api/v1/workspaces/{workspace_id}/evaluation/run`
- **Auth Required:** Bearer Token

#### Request Body (`application/json`):
```json
{
  "dataset_path": "backend/tests/fixtures/golden_evaluation_dataset.jsonl",
  "top_k": 5,
  "use_fake_llm": true,
  "use_fake_embeddings": true,
  "output_path": null
}
```

#### Response (`202 Accepted`):
```json
{
  "status": "completed",
  "message": "Evaluation completed successfully",
  "results": {
    "total_questions": 46,
    "aggregate_metrics": {
      "retrieval": {
        "avg_precision_at_k": 0.8043,
        "avg_recall_at_k": 0.8043,
        "avg_mrr": 1.0000
      },
      "citation": {
        "avg_resolution_rate": 1.0000,
        "avg_grounding_rate": 0.9674,
        "avg_hallucination_rate": 0.0000
      },
      "abstention": {
        "accuracy": 0.8913,
        "false_abstention_rate": 0.0870,
        "false_answer_rate": 0.0217
      },
      "deterministic_context": {
        "avg_context_precision": 0.7847,
        "avg_context_recall": 0.9348,
        "avg_f1_token_overlap": 0.4996,
        "evaluation_type": "deterministic_heuristic_pure_function"
      }
    }
  }
}
```

---

### 8.2 Get Latest Evaluation Results
- **Endpoint:** `GET /api/v1/workspaces/{workspace_id}/evaluation/results`
- **Auth Required:** Bearer Token

---

## 9. System Diagnostics & Health Endpoints

### 9.1 Service Liveness Check
- **Endpoint:** `GET /health`
- **Auth Required:** No

#### Response (`200 OK`):
```json
{
  "status": "healthy",
  "service": "enterprise-intelligence-platform",
  "version": "0.1.0"
}
```

---

### 9.2 Service Readiness Check
- **Endpoint:** `GET /ready`
- **Auth Required:** No

#### Response (`200 OK`):
```json
{
  "status": "ready",
  "database": "connected",
  "vector_store": "ready"
}
```


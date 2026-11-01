# Enterprise Intelligence Platform — API Reference & Endpoint Specification

## 1. Overview
The Enterprise Intelligence Platform exposes a RESTful HTTP API documented with OpenAPI v3. All requests and responses use JSON format, except document upload endpoints which accept multipart/form-data.

- **Base URL:** `http://localhost:8000`
- **API Prefix:** `/api/v1`
- **Interactive Swagger Docs:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## 2. Authentication
All protected endpoints require an `Authorization` header containing a valid signed JWT Bearer token:
```http
Authorization: Bearer <access_token>
```

---

## 3. Endpoints Catalog

### Health & Monitoring
| Method | Path | Auth | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | None | Liveness probe returning service status and timestamp. |
| `GET` | `/ready` | None | Readiness probe validating database connectivity. |

#### Sample `/health` Response:
```json
{
  "status": "ok",
  "service": "Enterprise Intelligence Platform",
  "version": "0.1.0",
  "environment": "development",
  "timestamp": "2026-10-31T22:17:47.659778+00:00"
}
```

---

### Authentication (`/api/v1/auth`)
| Method | Path | Auth | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register` | None | Register a new user and automatically provision a default workspace. |
| `POST` | `/api/v1/auth/login` | None | Authenticate with email and password to receive JWT token. |
| `GET` | `/api/v1/auth/me` | Bearer | Retrieve profile information for current authenticated user. |

#### Sample Registration Request:
```json
{
  "email": "engineer@enterprise.io",
  "password": "SecurePassword123!",
  "full_name": "Senior Cloud Architect",
  "role": "engineer"
}
```

---

### Workspaces (`/api/v1/workspaces`)
| Method | Path | Auth | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/workspaces` | Bearer | Create a new isolated engineering workspace. |
| `GET` | `/api/v1/workspaces` | Bearer | List all workspaces owned by or shared with current user. |
| `GET` | `/api/v1/workspaces/{workspace_id}` | Bearer | Get single workspace details. |

---

### Document Management (`/api/v1/workspaces/{workspace_id}/documents`)
| Method | Path | Auth | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/.../upload` | Bearer | Multipart file upload (PDF, Markdown, TXT, CSV, JSON) with SHA-256 deduplication and automatic chunking + embedding. |
| `GET` | `/...` | Bearer | List all indexed documents in workspace. |
| `GET` | `/.../{document_id}` | Bearer | Get document details and indexing status. |
| `GET` | `/.../{document_id}/chunks` | Bearer | Retrieve all indexed text chunks and structural metadata. |
| `DELETE` | `/.../{document_id}` | Bearer | Delete document record, chunks, and file on disk. |

---

### Search & Knowledge Retrieval
| Method | Path | Auth | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/workspaces/{workspace_id}/search` | Bearer | Search documents using `dense`, `sparse` (BM25), or `hybrid` (Reciprocal Rank Fusion). |

#### Sample Search Request:
```json
{
  "query": "PostgreSQL connection pool outage incident",
  "workspace_id": "0d182283-4a11-409b-a496-c189b88eb348",
  "top_k": 3,
  "mode": "hybrid"
}
```

#### Sample Search Response:
```json
{
  "query": "PostgreSQL connection pool outage incident",
  "mode": "hybrid",
  "total_results": 1,
  "results": [
    {
      "chunk_id": "4b54e7d1-e63b-4835-9005-d8cf22622e03",
      "document_id": "84e5ea90-f227-463d-82d3-1c39029a19c6",
      "document_title": "incident_104_db_pool_outage",
      "content": "On 2026-03-15 at 14:22 UTC, the PostgreSQL connection pool exhausted all 200 connections...",
      "score": 0.03279,
      "chunk_index": 0,
      "metadata": {
        "page_number": 1,
        "token_count": 84
      }
    }
  ]
}
```

---

### Grounded RAG Chat (`/api/v1/workspaces/{workspace_id}/chat`)
| Method | Path | Auth | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/workspaces/{workspace_id}/chat` | Bearer | Generate source-grounded answer with short citation mapping, abstention checks, and anti-hallucination guard. |

#### Sample Chat Request:
```json
{
  "query": "What occurred during Incident 104 and how was it mitigated?",
  "workspace_id": "0d182283-4a11-409b-a496-c189b88eb348",
  "top_k": 3
}
```

#### Sample Chat Response:
```json
{
  "answer": "Based on the engineering postmortem [c_0], on 2026-03-15 at 14:22 UTC, the PostgreSQL connection pool exhausted all 200 connections due to a missing index and transaction leak. The resolution involved adjusting max_connections to 400 and reducing the connection timeout to 5s.",
  "conversation_id": "bf86c990-27f1-432d-8e4a-b1451159b34a",
  "message_id": "3127814b-2b47-4e32-9c92-386d9a9ba420",
  "citations": [
    {
      "marker": "[c_0]",
      "document_id": "84e5ea90-f227-463d-82d3-1c39029a19c6",
      "document_title": "incident_104_db_pool_outage",
      "chunk_id": "4b54e7d1-e63b-4835-9005-d8cf22622e03",
      "snippet": "On 2026-03-15 at 14:22 UTC, the PostgreSQL connection pool exhausted all 200 connections...",
      "score": 0.03279
    }
  ],
  "is_abstention": false,
  "ungrounded_claims": [],
  "model_used": "fake-claude-3-5-sonnet",
  "provider_used": "fake_primary",
  "latency_ms": 12
}
```

---

### Autonomous Agents (`/api/v1/workspaces/{workspace_id}/agent`)
| Method | Path | Auth | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/.../investigate` | Bearer | Trigger autonomous multi-step reasoning investigation loop (Search -> Analyze -> Report). |
| `GET` | `/.../runs` | Bearer | List all autonomous agent runs for workspace. |
| `GET` | `/.../runs/{run_id}` | Bearer | Retrieve run details, tool execution traces, and final report. |

#### Sample Investigation Request:
```json
{
  "task": "Investigate root cause and remediation for PostgreSQL connection pool exhaustion",
  "workspace_id": "0d182283-4a11-409b-a496-c189b88eb348",
  "max_steps": 3
}
```


# API Documentation Index

Welcome to the API specification and integration documentation for the **Engineering Intelligence Platform (EIP)**.

## Quick Links
- **Comprehensive API Reference:** [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- **Interactive OpenAPI Swagger UI:** Accessible at `http://127.0.0.1:8000/docs` when the backend is running.
- **ReDoc Documentation:** Accessible at `http://127.0.0.1:8000/redoc`.
- **Raw OpenAPI Schema:** `http://127.0.0.1:8000/openapi.json`.

---

## Endpoint Groups Overview

| Tag | Base Path | Description | Authentication |
| :--- | :--- | :--- | :--- |
| **Authentication** | `/api/v1/auth` | User registration, login, JWT token issuance, and user profile. | Public / Bearer Token |
| **Workspaces** | `/api/v1/workspaces` | Multi-tenant workspace creation, listing, and tenant scoping. | Bearer Token |
| **Documents** | `/api/v1/workspaces/{id}/documents` | Multipart document upload (PDF, TXT, MD, CSV), processing status, and chunk inspection. | Bearer Token |
| **Search & RAG Chat** | `/api/v1/workspaces/{id}` | Hybrid retrieval (Dense + BM25) and evidence-grounded conversational question answering. | Bearer Token |
| **Conversations** | `/api/v1/workspaces/{id}/conversations` | Multi-turn conversation sessions, message history, and citation retention. | Bearer Token |
| **Autonomous Agent** | `/api/v1/workspaces/{id}/agent` | Multi-step technical investigation workflows (Search, Analyze, Report). | Bearer Token |
| **Evaluation** | `/api/v1/workspaces/{id}/evaluation` | Benchmark test execution across 46 golden questions and quantitative metric retrieval. | Bearer Token |
| **Health** | `/health`, `/ready` | Service liveness, database connectivity, and vector engine readiness probes. | Public |

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for full request/response schemas, JSON payloads, and cURL examples.


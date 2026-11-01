# CLAUDE.md — AI Engineering Assistant Guide

## Project Overview

The **Engineering Intelligence Platform (EIP)** is an enterprise knowledge retrieval, technical investigation, and document intelligence platform. It ingests heterogeneous technical documentation (incident reports, postmortems, architecture specifications, runbooks, and CSV logs), chunks and vectorizes content into PostgreSQL with `pgvector`, and provides an evidence-grounded Retrieval-Augmented Generation (RAG) pipeline and autonomous multi-tool agent.

---

## Architectural Summary

- **Backend Runtime:** Python 3.11+ / FastAPI modular monolith with Uvicorn async ASGI server.
- **Frontend Client:** React 18, Vite 5, TypeScript, Tailwind CSS, Lucide React, and React Router v6.
- **Primary Database:** PostgreSQL 16 with the `pgvector` extension for unified relational and 1536-dimensional vector storage. SQLite fallback supported for fast local unit testing.
- **Database Migrations:** Alembic (`backend/alembic/`) with current head revision `58f1a23b49de`.
- **Hybrid Retrieval:** Dense cosine similarity (`pgvector`) + Sparse lexical matching (BM25) fused via Reciprocal Rank Fusion (RRF, $k=60$).
- **RAG Guardrails:** `EvidenceSufficiencyGate` ($< 25\%$ coverage short-circuits to honest abstention; PRIMARY/SUPPLEMENTARY chunk triage; date/numerical conflict detection), XML untrusted context isolation, and `verify_claim_grounding` verifier.
- **LLM Provider Orchestration:** `BaseLLMClient` with Anthropic Claude 3.5 Sonnet (primary), OpenAI GPT-4o (secondary fallback), and deterministic `FakeLLMClient` for offline testing. Automatic circuit breaker failover.
- **Autonomous Agent:** Custom `AgentOrchestrator` coordinating 3 tools (`Knowledge Base Search`, `Document Analysis`, `Structured Report Generation`) with max 5 steps, Pydantic parameter validation, and loop limits.
- **Conversational Memory:** Multi-session conversation management with sliding-window token budgeting.
- **Observability:** Langfuse v5 tracer (`@observe` decorators with fail-safe local bypass) and single-entry `llm_logs` usage telemetry.

---

## Repository Directory Structure

```
enterprise-intelligence-platform/
├── backend/
│   ├── alembic/              # Alembic migration scripts and env.py
│   │   └── versions/         # Versioned migration revisions (47e95deb65dd -> 58f1a23b49de)
│   ├── app/
│   │   ├── agents/           # Autonomous agent orchestrator & tool definitions
│   │   ├── api/              # FastAPI route controllers & dependency injection
│   │   ├── core/             # Application configuration (Pydantic Settings) & security
│   │   ├── db/               # Database session manager, base model, & custom VectorType
│   │   ├── document_processing/ # Ingestion parsers (PyMuPDF, MD, CSV, TXT) & chunker
│   │   ├── llm/              # Provider clients (Claude, OpenAI, Fake) & fallback router
│   │   ├── models/           # SQLModel / SQLAlchemy database entity models
│   │   ├── observability/    # Langfuse v5 tracer integration
│   │   ├── rag/              # Evidence gate, grounding verifier, & prompt templates
│   │   ├── repositories/     # Data access layer (vector repository)
│   │   ├── retrieval/        # Hybrid dense/sparse search & RRF fusion
│   │   ├── schemas/          # Pydantic v2 API request/response schemas
│   │   └── services/         # Core business logic (RAG service, document service)
│   ├── evaluation/           # 46-question golden benchmark runner & heuristic metrics
│   ├── tests/
│   │   ├── fixtures/         # Golden dataset (jsonl) & synthetic markdown documents
│   │   ├── integration/      # End-to-end API & PostgreSQL integration tests
│   │   ├── security/         # Prompt injection & security test harness
│   │   └── unit/             # Fast unit test suites (auth, rag, agent, router, etc.)
│   ├── requirements.txt      # Python backend dependencies
│   └── alembic.ini           # Alembic database migration configuration
├── frontend/
│   ├── src/
│   │   ├── components/       # Reusable React components (Navbar, Sidebar, Modals)
│   │   ├── context/          # AuthContext & WorkspaceContext
│   │   ├── pages/            # Page views (Login, Chat, Documents, Agent, Evaluation, Settings)
│   │   ├── services/         # Axios API service layer (auth, chat, documents, evaluation)
│   │   └── types/            # TypeScript interfaces mirroring backend schemas
│   ├── package.json          # Node.js dependencies (React, Vite, Tailwind, Vitest)
│   └── vite.config.ts        # Vite build & proxy configuration
├── docs/                     # Architectural specs, database ERDs, API docs, and PRDs
├── storage/                  # Local persistent document upload storage
└── docker-compose.yml        # Docker Compose multi-service definition
```

---

## Setup & Environment Configuration

### 1. Python Virtual Environment (Backend)
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r backend/requirements.txt
```

### 2. Frontend Node Environment
```bash
cd frontend
npm install
cd ..
```

### 3. Environment Variables (`.env`)
Create `.env` in the project root based on `backend/.env.example`:
```ini
# Application Core
ENVIRONMENT=development
PROJECT_NAME="Engineering Intelligence Platform"
SECRET_KEY=change-this-to-a-secure-random-key-at-least-32-chars-long
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Database
DATABASE_URL=postgresql://eip_user:eip_password@localhost:5432/engineering_intelligence
# Or local SQLite fallback:
# DATABASE_URL=sqlite:///./engineering_intelligence.db

# LLM Providers & Testing
USE_FAKE_LLM=true
USE_FAKE_EMBEDDINGS=true
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Observability (Optional)
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=https://cloud.langfuse.com
```

---

## Testing & Build Commands

All code modifications must pass the complete test battery with zero regressions:

### 1. Run Complete Backend Pytest Suite (149 tests)
```bash
python -m pytest backend/tests
```

### 2. Run Security & Prompt Injection Test Harness
```bash
python -m pytest backend/tests/security/test_security_suite.py -v
```

### 3. Run Security Remediation Verification
```bash
python -m pytest backend/tests/unit/test_security_remediation.py -v
```

### 4. Run Golden Evaluation Benchmark (46 Questions)
```bash
python -m backend.evaluation.runner
```

### 5. Run Frontend Vitest Suite
```bash
cd frontend && npm test -- --run
```

### 6. Run Frontend Production TypeScript Build
```bash
cd frontend && npm run build
```

---

## Database Migration Workflow (Alembic)

The repository uses Alembic for schema migrations. All migrations must be checked before submitting changes:

```bash
# View current database revision
python -m alembic -c backend/alembic.ini current

# View available migration heads (Current Head: 58f1a23b49de)
python -m alembic -c backend/alembic.ini heads

# Upgrade database to head revision
python -m alembic -c backend/alembic.ini upgrade head

# Roll back the latest migration
python -m alembic -c backend/alembic.ini downgrade -1

# Generate a new migration revision
python -m alembic -c backend/alembic.ini revision --autogenerate -m "describe_changes"
```

---

## Development & Coding Conventions

### Python & Backend Standards
1. **Type Annotations:** Strictly annotate all function signatures, parameters, and return types.
2. **Pydantic v2 Schemas:** Keep schemas in `backend/app/schemas/`. Use `model_config = ConfigDict(from_attributes=True)` for ORM compatibility.
3. **Database Sessions:** Always use dependency injection `db: Session = Depends(get_db)`. Never instantiate raw database sessions manually in endpoints.
4. **Error Handling:** Raise standard `HTTPException` with explicit status codes (`400`, `401`, `403`, `404`, `409`, `422`, `500`).
5. **Single-Entry Telemetry:** The `LLMFallbackRouter` must log exactly 1 record per user request in `llm_logs` (`is_fallback=True` if failover occurred). Never double-count failed attempts.

### Frontend Standards
1. **TypeScript Strictness:** Maintain strict typing without `any` where possible. Types must mirror backend Pydantic schemas in `frontend/src/types/index.ts`.
2. **Honest States:** Display actual backend-produced data. Never fabricate metrics, simulate fake latency, or use silent fallback data that masks backend failures.
3. **Component Modularity:** Reusable UI components belong in `frontend/src/components/`; page routes belong in `frontend/src/pages/`.

---

## Security Rules & Guardrails

1. **Zero Credentials in Git:** Never commit API keys, passwords, or production secrets. Use `.env.example` as a sanitized template.
2. **Workspace Isolation:** Every database entity belongs to a `workspace_id`. Always verify user access via `verify_workspace_access(workspace_id, current_user, db)`.
3. **Prompt Injection Quarantine:** Document chunks passed to LLMs must be quarantined inside `<untrusted_document_context>` XML delimiters with defensive system instructions.
4. **Honest Uncertainty & Abstention:** When evidence coverage is $< 25\%$ or context is insufficient, the system must return an honest abstention notice rather than hallucinating.
5. **Preserve OpenCode Phase 8 Security Validators:** Do not weaken the `SECRET_KEY` ($\ge 32$ chars in production) or `CORS_ORIGINS` validators in `backend/app/core/config.py`.


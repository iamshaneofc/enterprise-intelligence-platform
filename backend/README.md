# Enterprise Intelligence Platform — Backend Architecture & Service Documentation

## 1. Overview
The **Enterprise Intelligence Platform (EIP)** backend is a production-grade AI platform engineered with **FastAPI**, **SQLAlchemy 2.0**, and **Pydantic v2**. It enables engineering organizations to ingest, index, retrieve, and autonomously investigate technical documentation, incident postmortems, architecture specifications, and runbooks.

---

## 2. Implemented Capabilities
- **Modular Monolith Architecture:** Thin API controllers delegating to domain services, repositories, and orchestrators.
- **Security & RBAC:** Argon2/Bcrypt password hashing, signed JWT Bearer authentication, and multi-tenant workspace isolation.
- **Multi-Format Ingestion:** Parsers for PDF (`pypdf`), Markdown, Plain Text, CSV, and JSON with SHA-256 deduplication and path sanitization.
- **Recursive Chunking:** Delimiter hierarchy preserving structural page numbers, section headers, and token estimates.
- **Embedding Pipeline:** Dual-mode OpenAI (`text-embedding-3-small`, 1536 dims) and deterministic unit-vector generator for test isolation.
- **Hybrid Search Engine:** Dense vector similarity + Sparse BM25 lexical search fused via Reciprocal Rank Fusion ($k=60$).
- **Anti-Hallucination Guard:** Deterministic regex verification ensuring all dates, metrics, and URLs in generated answers exist in source evidence chunks.
- **Short Citation Aliasing:** Context mapped to short aliases `[c_0]`, `[c_1]` inside `<untrusted_document_context>` XML wrappers to eliminate prompt hallucination.
- **LLM Circuit Breaker Fallback:** Seamless automatic failover from Primary (Anthropic Claude 3.5 Sonnet) to Fallback (OpenAI GPT-4o) on rate limits (429) or timeouts, with comprehensive usage logging.
- **Conversational Memory:** Sliding context windows (last 4 turns) with pronoun coreference resolution.
- **Autonomous Agent Trio:** Constrained tool-calling loop (Search, Analysis, Report Generation) with 5-step cap and full execution trace persistence.

---

## 3. Directory Layout
```
backend/
├── app/
│   ├── api/
│   │   ├── dependencies.py          # JWT auth & workspace scoping
│   │   └── routes/
│   │       ├── auth.py              # Register, login, profile
│   │       ├── health.py            # /health & /ready probes
│   │       ├── workspaces.py        # Workspace CRUD
│   │       ├── documents.py         # Multipart upload & chunk inspection
│   │       ├── chat.py              # Hybrid search & grounded RAG
│   │       ├── conversations.py     # Conversation history & citations
│   │       └── agent.py             # Autonomous investigation runs
│   ├── core/
│   │   ├── config.py                # Pydantic v2 BaseSettings
│   │   ├── security.py              # Bcrypt & PyJWT handlers
│   │   ├── exceptions.py            # Typed domain exceptions
│   │   └── logging.py               # Structured logging
│   ├── db/
│   │   ├── session.py               # SQLAlchemy 2.0 engine & session
│   │   └── types.py                 # Hybrid SQLite / PostgreSQL VectorType
│   ├── document_processing/
│   │   ├── storage.py               # File persistence & SHA-256 deduplication
│   │   ├── parsers.py               # PDF, Markdown, CSV, JSON parsers
│   │   └── chunker.py               # Recursive chunker with metadata
│   ├── embeddings/
│   │   └── provider.py              # OpenAI & deterministic fake providers
│   ├── repositories/
│   │   └── vector_repo.py           # Dense cosine & sparse BM25 repository
│   ├── retrieval/
│   │   └── hybrid.py                # Reciprocal Rank Fusion (RRF k=60)
│   ├── rag/
│   │   ├── prompt_templates.py      # XML context & short citation prompt
│   │   ├── citations.py             # [c_X] CitationMap resolver
│   │   └── grounding.py             # Deterministic anti-hallucination guard
│   ├── llm/
│   │   ├── base.py                  # Base LLM client interface
│   │   ├── anthropic_client.py      # Claude 3.5 Sonnet client
│   │   ├── openai_client.py         # GPT-4o client
│   │   ├── fake_client.py           # Deterministic test generator
│   │   └── router.py                # Automatic failover & telemetry
│   ├── memory/
│   │   └── manager.py               # Sliding context & query reformulation
│   ├── agents/
│   │   ├── tools.py                 # Search, Analysis, Report tools
│   │   └── orchestrator.py          # 5-step autonomous reasoning loop
│   ├── services/
│   │   ├── document_service.py      # Document lifecycle coordinator
│   │   └── rag_service.py           # RAG pipeline coordinator
│   ├── models/                      # SQLAlchemy 2.0 ORM models
│   ├── schemas/                     # Pydantic v2 request/response schemas
│   └── main.py                      # FastAPI application entrypoint
├── tests/
│   ├── conftest.py                  # In-memory SQLite fixtures & TestClient
│   ├── unit/                        # 25 unit test cases
│   ├── integration/                 # End-to-end integration test
│   └── fixtures/                    # Synthetic postmortems & golden dataset
├── Dockerfile                       # Multi-stage production Docker image
├── requirements.txt                 # Pinned dependencies
└── .env.example                     # Environment configuration template
```

---

## 4. Getting Started

### Local Setup
```bash
# 1. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env

# 4. Start backend server
uvicorn backend.app.main:app --reload --port 8000
```

### Running Tests
Execute the complete test suite:
```bash
python -m pytest backend/tests/ -v
```

### Docker Deployment
```bash
docker-compose up --build -d
```
Service will be available at `http://localhost:8000` with interactive Swagger docs at `http://localhost:8000/docs`.

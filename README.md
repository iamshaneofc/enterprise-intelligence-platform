# Engineering Intelligence Platform (EIP)

> **Enterprise Document Intelligence • Grounded RAG • Autonomous Multi-Tool Agent • Systematic Evaluation**  
> **Repository:** [https://github.com/iamshaneofc/enterprise-intelligence-platform](https://github.com/iamshaneofc/enterprise-intelligence-platform)  
> **Live Production URL (Vercel):** [https://enterprise-intelligence-platform-dun.vercel.app](https://enterprise-intelligence-platform-dun.vercel.app)  
> **Live Production Backend (AWS EC2):** `https://treaty-finest-equality-dot.trycloudflare.com` (proxied to `13.207.43.212:8000`)  
> **Current Status:** `DEPLOYED, IMPLEMENTED & VERIFIED` (Full AWS RDS & EC2 Cloud Deployment • Vercel Frontend • Unit & Integration Test Suite • 46-Question Golden Evaluation Benchmark)

---

## 1. Project Overview

The **Engineering Intelligence Platform (EIP)** is a production-grade AI knowledge and technical investigation system designed to eliminate technical knowledge fragmentation across software engineering, DevOps, and Site Reliability Engineering (SRE) teams.

Modern engineering organizations manage thousands of disparate technical records: incident postmortems, architecture specifications, deployment procedures, infrastructure runbooks, and operational logs. When an incident occurs or an architecture decision is evaluated, engineers spend valuable hours manually searching through scattered repositories to answer critical questions:
- *What was the documented root cause of the last database connection outage?*
- *Which services were degraded when Envoy latency spiked?*
- *What were the verified resolution steps taken during Incident 104?*

Off-the-shelf conversational AI tools fail in engineering environments because they hallucinate plausible root causes, cannot cite exact source passages, silently overlook contradictions across documents, and cannot execute multi-step investigation plans.

The Engineering Intelligence Platform solves this through:
1. **Zero-Trust Information Ingestion:** Processing multi-format technical documents (`.pdf`, `.txt`, `.md`, `.csv`) with SHA-256 deduplication and semantic chunking.
2. **Hybrid Vector & Lexical Retrieval:** Combining dense semantic search (`pgvector`) with sparse BM25 keyword matching via Reciprocal Rank Fusion (RRF, $k=60$).
3. **Rigorous Evidence Gate & Claim Grounding:** Filtering distractors, detecting date and numerical conflicts, enforcing a $< 25\%$ coverage short-circuit to honest abstention, and verifying all assertions against cited chunks.
4. **Intelligent Multi-Provider Failover:** Automatic circuit-breaker fallback between Anthropic Claude 3.5 Sonnet and OpenAI GPT-4o with single-entry token accounting.
5. **Autonomous Multi-Tool Agent:** Executing multi-step investigations via three specialized tools: Knowledge Base Search, Document Analysis, and Structured Report Generation.
6. **Empirical Evaluation Benchmark:** A 46-question golden evaluation suite measuring retrieval precision, context recall, grounding faithfulness, and abstention accuracy.
7. **End-to-End Observability:** Full telemetry logging in PostgreSQL (`llm_logs`) and native Langfuse v5 request tracing.

### Live Production Interface

| Multi-Hop Grounded Synthesis with Citations (`[c_1]`, `[c_2]`) | Honest Model Abstention via Evidence Gate |
| :---: | :---: |
| ![Grounded Incident Chat](docs/images/eip_live_grounded_chat.png) | ![Honest Model Abstention](docs/images/eip_live_model_abstention.png) |
| *Synthesizing causal incident chains with verified source citations* | *Evidence sufficiency gate preventing hallucinations on out-of-domain queries* |

---

## 2. Implemented Features & Modules

| Module | Implementation Status | Core Technical Capabilities |
| :--- | :---: | :--- |
| **Module A: Document Intelligence** | `VERIFIED` | Native parsers for PDF (PyMuPDF / fitz), Markdown, CSV, and TXT. SHA-256 deduplication, recursive semantic chunking, and 1536-dimensional vector embedding. |
| **Module B: Advanced RAG Architecture** | `VERIFIED` | Hybrid retrieval (Dense `pgvector` + Sparse BM25) fused via Reciprocal Rank Fusion. Passage citations (`[c_0]`). `EvidenceSufficiencyGate` with conflict detection and honest abstention. |
| **Module C: LLM Integration & Fallback** | `VERIFIED` | Unified `BaseLLMClient` supporting Anthropic Claude 3.5 Sonnet, OpenAI GPT-4o, and deterministic `FakeLLMClient`. Automatic circuit-breaker failover with single-entry token and cost tracking. |
| **Module D: Autonomous AI Agent** | `VERIFIED` | Custom `AgentOrchestrator` coordinating 3 functional tools: Knowledge Base Search, Document Analysis, and Structured Report Generation. Pydantic parameter validation, step caps (max 5), and self-correction. |
| **Module E: Conversational Memory** | `VERIFIED` | Multi-turn conversation management with database persistence, message threading, citation retention, and sliding-window token budgeting. |
| **Module F: Application Dashboard** | `VERIFIED` | Responsive React 18 / Vite 5 / TypeScript SPA with Tailwind CSS. Includes auth, workspace management, document manager with chunk explorer modal, grounded chat with citation drawers, agent timeline visualizer, and live evaluation dashboard. |
| **Module G: AI Evaluation Framework** | `VERIFIED` | 46-question golden evaluation dataset (`golden_evaluation_dataset.jsonl`), automated runner (`backend.evaluation.runner`), deterministic heuristic metrics, and live API endpoints. |
| **Advanced Challenge: Prompt Injection Defense** | `VERIFIED` | All retrieved context encapsulated within `<untrusted_document_context>` XML tags with defensive system prompt rules preventing instruction hijacking. |
| **Observability & Telemetry** | `VERIFIED` | Native `llm_logs` database table tracking prompt/completion/cached tokens, latency, cost USD, and error types. Langfuse v5 tracer (`@observe` decorators with fail-safe local bypass). |

---

## 3. Architecture & Technology Stack

```
+--------------------------------------------------------------------------------------------------+
|                                    TECHNOLOGY STACK SUMMARY                                      |
+--------------------------+------------------------------+----------------------------------------+
| Architectural Tier       | Selected Technology          | Purpose & Architectural Role           |
+--------------------------+------------------------------+----------------------------------------+
| Client Application       | React 18, Vite 5, TypeScript | Responsive, type-safe Single-Page App  |
| UI & Styling             | Tailwind CSS, Lucide React   | Enterprise SaaS design system          |
| Backend API Server       | Python 3.11+ / FastAPI       | High-throughput async REST API runtime |
| Primary Database         | PostgreSQL 16 + pgvector     | Unified relational metadata & vectors  |
| Development Fallback DB  | SQLite (JSON serialized)     | Fast, zero-dependency unit testing     |
| Database Migrations      | Alembic                      | Version-controlled schema evolutions   |
| Primary LLM Provider     | OpenAI GPT-4o (Production)    | Grounded RAG synthesis & agent reasoning |
| Fallback LLM Provider    | Anthropic Claude 3.5 Sonnet   | Circuit-breaker failover resilience    |
| Embedding Model          | OpenAI text-embedding-3-small | 1536-dimensional vector representations|
| Document Parsers         | PyMuPDF (fitz), CSV, MD, TXT | Multi-format technical text extraction |
| Observability & Tracing  | Langfuse v5 + SQLAlchemy Logs| Request-level tracing & token telemetry|
| Containerization         | Docker & Docker Compose      | Multi-service containerized deployment |
+--------------------------+------------------------------+----------------------------------------+
```

### Complete System Architecture Diagram

```mermaid
flowchart TD
    subgraph CLIENT_TIER ["Client Presentation Tier (React 18 + Vite + TypeScript)"]
        UI_AUTH["Auth & Workspace Guard"]
        UI_DOCS["Document Manager & Chunk Explorer"]
        UI_CHAT["Grounded RAG Chat & Citations"]
        UI_AGENT["Agent Studio & Step Timeline"]
        UI_EVAL["Live Evaluation Dashboard"]
    end

    subgraph API_GATEWAY ["FastAPI ASGI Application Server (Port 8000)"]
        API_AUTH["/api/v1/auth (Register, Login, Me)"]
        API_WS["/api/v1/workspaces"]
        API_DOCS["/api/v1/workspaces/{id}/documents"]
        API_CHAT["/api/v1/workspaces/{id}/chat"]
        API_SEARCH["/api/v1/workspaces/{id}/search"]
        API_AGENT["/api/v1/workspaces/{id}/agent/investigate"]
        API_CONV["/api/v1/workspaces/{id}/conversations"]
        API_EVAL["/api/v1/workspaces/{id}/evaluation/run"]
        API_HEALTH["/health & /ready"]
    end

    subgraph CORE_SERVICES ["Core Intelligence & Service Layer"]
        DOC_SVC["Document Ingestion & Parsers"]
        CHUNK_SVC["Recursive Semantic Chunker"]
        RAG_SVC["RAG Service Orchestrator"]
        GATE_SVC["Evidence Sufficiency Gate"]
        VERIFY_SVC["Claim Grounding Verifier"]
        HYBRID_SVC["Hybrid Retrieval (Dense + BM25)"]
        AGENT_SVC["Autonomous Agent Engine"]
        MEM_SVC["Conversational Memory Manager"]
        LLM_ROUTER["LLM Provider Fallback Router"]
    end

    subgraph AGENT_TOOLS ["Controlled Agent Tools"]
        T1["Knowledge Base Search"]
        T2["Document Analysis"]
        T3["Structured Report Generation"]
    end

    subgraph PERSISTENCE ["Persistence Tier (PostgreSQL 16 + pgvector / SQLite)"]
        DB_USERS[("users")]
        DB_WORKSPACES[("workspaces & members")]
        DB_DOCS[("documents & chunks")]
        DB_CONV[("conversations & messages")]
        DB_CITATIONS[("citations")]
        DB_RUNS[("agent_runs & tool_executions")]
        DB_LOGS[("llm_logs (tokens & cost)")]
        LOCAL_STORAGE[("Local File Storage")]
    end

    subgraph LLM_PROVIDERS ["LLM Provider Tier"]
        CLAUDE["Anthropic Claude 3.5 Sonnet (Primary)"]
        OPENAI["OpenAI GPT-4o (Fallback)"]
        FAKE_LLM["FakeLLMClient (Test Mode)"]
    end

    CLIENT_TIER -->|HTTPS / REST API| API_GATEWAY
    API_GATEWAY --> CORE_SERVICES

    DOC_SVC --> CHUNK_SVC --> DB_DOCS
    DOC_SVC --> LOCAL_STORAGE

    RAG_SVC --> HYBRID_SVC --> DB_DOCS
    RAG_SVC --> GATE_SVC
    RAG_SVC --> LLM_ROUTER
    RAG_SVC --> VERIFY_SVC
    RAG_SVC --> MEM_SVC --> DB_CONV
    RAG_SVC --> DB_CITATIONS

    AGENT_SVC --> AGENT_TOOLS
    T1 --> HYBRID_SVC
    T2 --> DB_DOCS
    T3 --> LLM_ROUTER
    AGENT_SVC --> DB_RUNS

    LLM_ROUTER --> CLAUDE
    LLM_ROUTER -.->|Failover| OPENAI
    LLM_ROUTER -.->|Test Mode| FAKE_LLM
    LLM_ROUTER --> DB_LOGS
```

---

## 4. Local Installation & Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- PostgreSQL 16 with `pgvector` extension (Optional; SQLite fallback is supported for local testing)

### Step 1: Clone Repository
```bash
git clone https://github.com/iamshaneofc/enterprise-intelligence-platform.git
cd enterprise-intelligence-platform
```

### Step 2: Backend Setup
```bash
# Create and activate Python virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install backend dependencies
pip install -r backend/requirements.txt
```

### Step 3: Frontend Setup
```bash
cd frontend
npm install
cd ..
```

### Step 4: Configure Environment Variables
Copy the template configuration file:
```bash
cp backend/.env.example .env
```

Edit `.env` as required:
```ini
ENVIRONMENT=development
PROJECT_NAME="Engineering Intelligence Platform"
SECRET_KEY=dev-secret-key-must-be-at-least-32-chars-long-for-production!
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Database (PostgreSQL or local SQLite)
DATABASE_URL=sqlite:///./engineering_intelligence.db

# LLM Providers (Set to true for deterministic testing without external API costs)
USE_FAKE_LLM=true
USE_FAKE_EMBEDDINGS=true

# For Live Production Generative Mode:
# USE_FAKE_LLM=false
# USE_FAKE_EMBEDDINGS=false
# ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...

# Observability (Optional)
# LANGFUSE_PUBLIC_KEY=pk-lf-...
# LANGFUSE_SECRET_KEY=sk-lf-...
# LANGFUSE_HOST=https://cloud.langfuse.com
```

### Step 5: Database Migrations
Initialize or upgrade the database schema using Alembic:
```bash
python -m alembic -c backend/alembic.ini upgrade head
```

### Step 6: Start Services
In Terminal 1 (FastAPI Backend):
```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

In Terminal 2 (Vite Frontend):
```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 3000
```

Open your browser at `http://127.0.0.1:3000`.

---

## 5. Docker Setup

A multi-service `docker-compose.yml` is provided for containerized execution with PostgreSQL and `pgvector`:

```bash
# Start all services (PostgreSQL + pgvector, Backend, Frontend)
docker compose up -d

# View container logs
docker compose logs -f backend

# Run database migrations inside container
docker compose exec backend alembic -c backend/alembic.ini upgrade head

# Tear down services
docker compose down
```

Services will be accessible at:
- **Frontend SPA:** `http://localhost:3000`
- **Backend API & Swagger Docs:** `http://localhost:8000/docs`
- **PostgreSQL Database:** `localhost:5432`

---

## 6. Comprehensive Test Execution

The codebase includes automated test suites across all layers:

```bash
# 1. Backend Unit & Integration Tests
python -m pytest backend/tests/unit backend/tests/integration

# 2. Backend Security & Prompt Injection Test Harness
python -m pytest backend/tests/security/test_security_suite.py -v

# 3. Backend Security Remediation Verification
python -m pytest backend/tests/unit/test_security_remediation.py -v

# 4. Golden Evaluation Benchmark (46 Questions)
python -m backend.evaluation.runner

# 5. Frontend Vitest Suite
cd frontend && npm test -- --run

# 6. Frontend Production TypeScript Build
cd frontend && npm run build
```

### Verified Test Coverage

| Suite | Scope | Status |
|---|---|---|
| Backend Unit & Integration | User registration, authentication, authorization, workspace isolation, end-to-end workflow | Verified |
| Frontend Vitest | API client, token management, markdown processing, evaluation service | 10 tests passing |
| Frontend Production Build | TypeScript compilation and Vite production bundle | 0 errors |
| Backend Health (`/health`) | AWS EC2 production endpoint | 200 OK |
| Backend Readiness (`/ready`) | Database connectivity check on AWS EC2 | 200 OK, database connected |

---

## 7. Golden Evaluation Benchmark Results

The platform is evaluated against a 46-question golden benchmark (`golden_evaluation_dataset.jsonl`) spanning six inquiry categories:

| Category | Query Count | Representation |
| :--- | :---: | :---: |
| `single_document_factoid` | 14 | 30.4% |
| `unanswerable` | 9 | 19.6% |
| `complex_reasoning` | 8 | 17.4% |
| `multi_document_synthesis` | 6 | 13.0% |
| `incident_timeline` | 5 | 10.9% |
| `conflict_handling` | 4 | 8.7% |
| **Total** | **46** | **100.0%** |

### Evaluation Methodology

Evaluation benchmarks are continuously refined to improve retrieval relevance, evidence grounding, response accuracy, and system reliability. Evaluation runs deterministically offline using `FakeLLMClient` and `FakeEmbeddings` with pure-function Information Retrieval metrics (Precision@K, Recall@K, MRR, NDCG@K with logarithmic discounting), citation resolution, and grounding verification.

Results are reported across two distributions to provide transparent signal:

- **All 46 Queries:** Includes 9 unanswerable queries. Per standard IR convention, queries with no relevant ground truth contribute 0.0 to retrieval metrics.
- **37 Answerable Queries Only:** Excludes unanswerable queries, showing retrieval performance on questions with supporting evidence.

### Corrected Benchmark Results (46-Question Golden Dataset)

| Metric | All 46 Queries | 37 Answerable Queries | Methodology |
| :--- | :---: | :---: | :--- |
| **Precision@5** | 0.2565 | 0.3189 | Formal IR: relevant retrieved / K |
| **Recall@5** | 0.7609 | 0.9459 | Formal IR: relevant retrieved / total relevant |
| **MRR** | 0.5996 | 0.7455 | Mean reciprocal rank of first relevant hit |
| **NDCG@5** | 0.6375 | 0.7926 | DCG/IDCG with log₂ position discount |
| **Context Faithfulness** | 1.0000 | 1.0000 | Claims verified against retrieved context |
| **Answer Correctness** | 0.8478 | 0.9189 | Semantic similarity to ground truth |
| **Abstention Accuracy** | 0.9130 | 1.0000 | Correct accept/abstain decisions |
| **False Answer Rate** | 0.0000 | 0.0000 | Unanswerable queries answered instead of abstained (live LLM) |

Evaluation results are computed using formal Information Retrieval formulations and are tracked per-query in the benchmark dataset. Detailed category-by-category breakdown and per-query results are preserved in [`docs/reports/evaluation_results_corrected.json`](docs/reports/evaluation_results_corrected.json) and [`docs/reports/FINAL_EVALUATION_ACCURACY_AUDIT.md`](docs/reports/FINAL_EVALUATION_ACCURACY_AUDIT.md).

---

## 8. 5-Minute Demonstration Walkthrough

Follow this sequence to test all platform capabilities (available both locally and on the live [Production Vercel Frontend](https://enterprise-intelligence-platform-dun.vercel.app)):

1. **Authentication:** Open the login page. Use the one-click demo account buttons (`Lead Architect` or `Senior Engineer`, password `demopassword2026!`), or create your own workspace account.
2. **Document Management:** Navigate to **Documents**. Upload an incident postmortem (e.g., from `backend/tests/fixtures/synthetic_docs/incident_104_postmortem.md` or a PDF runbook). Watch status transition from `PENDING` to `INDEXED`. Click **View Chunks** to inspect chunk boundaries, tokens, and metadata.
3. **Evidence-Grounded Chat:** Open **Chat**. Ask an investigative question: *"How did the cache configuration change affect database CPU and p95 latency?"* Observe the streaming response with verified citation markers (`[c_0]`). Click the citation badge to inspect the exact source passage in the side drawer.
4. **Honest Abstention:** Ask an unanswerable or out-of-domain question: *"What was the monthly cloud infrastructure bill for this service?"* The `EvidenceSufficiencyGate` detects insufficient evidence and returns an honest, structured abstention alert rather than fabricating numbers.
5. **Autonomous Investigation:** Open **Agent Studio**. Enter: *"Investigate recurring database connection failures across all incident reports and compile an executive report."* Observe the live execution timeline as the agent calls `Knowledge Base Search`, pipes results to `Document Analysis`, and outputs a formatted Markdown report via `Structured Report Generation`.
6. **Live Evaluation Dashboard:** Open **Evaluation**. Click **Run Evaluation Benchmark** to execute the golden evaluation suite live against the backend, rendering real aggregate metrics and category breakdowns with zero disruption to the production environment.
7. **System Diagnostics:** Open **Settings** to inspect active workspace configuration, token telemetry, and health check statuses.

---

## 9. Production Deployment & Cloud Architecture

### Production Deployment Architecture

```
Vercel Frontend (HTTPS)  ──►  Cloudflare Tunnel  ──►  FastAPI Backend (AWS EC2 i-08a9c6aff142a77d4)  ──►  AWS RDS PostgreSQL 16 (pgvector)
```

| Component | Cloud Provider & Identifier | Production Endpoint | Live Status |
| :--- | :--- | :--- | :--- |
| **Frontend SPA** | Vercel (Edge Network) | [enterprise-intelligence-platform-dun.vercel.app](https://enterprise-intelligence-platform-dun.vercel.app) | `200 OK`, Live React 18 SPA |
| **Backend API Gateway** | Cloudflare Tunnel (HTTPS) | `https://treaty-finest-equality-dot.trycloudflare.com` | `200 OK`, Proxied to EC2 |
| **Backend Host** | AWS EC2 `i-08a9c6aff142a77d4` (`ap-south-1`) | `http://13.207.43.212/health` | `200 OK`, `environment=production` |
| **Backend Readiness** | AWS EC2 `i-08a9c6aff142a77d4` (`ap-south-1`) | `http://13.207.43.212/ready` | `200 OK`, `database=connected` |
| **Primary Database** | AWS RDS PostgreSQL 16 + `pgvector` | Internal VPC Endpoint | Connected, Relational + Vector store |
| **Active LLM Provider**| OpenAI `gpt-4o` | Managed API | Active (`USE_FAKE_LLM=false`) |
| **Active Embeddings**  | OpenAI `text-embedding-3-small` (1536-dim) | Managed API | Active (`USE_FAKE_EMBEDDINGS=false`) |

### Demo Accounts for Live Verification

The deployed application includes two pre-configured enterprise demo accounts with one-click credential autofill on the login page:

| Role | Work Email | Password | Access Level |
| :--- | :--- | :--- | :--- |
| **Lead Architect** | `lead.architect@enterprise.io` | `demopassword2026!` | Workspace Admin (Full document ingestion, agent studio, evaluation) |
| **Senior Engineer** | `engineer@enterprise.io` | `demopassword2026!` | Engineer (Document search, chat investigation, chunk exploration) |

### Security & Non-Root Container Execution

- **Zero committed secrets:** All API keys and connection strings are managed securely via AWS EC2 environment configuration and Vercel project environment variables.
- **Unprivileged Container User:** The production Docker container executes as non-root `appuser` (UID 1000) with dependencies isolated in `/opt/venv`.
- **CORS Hardening:** Production origins are strictly restricted to the verified Vercel frontend domain.

---

## 10. Recent Engineering Improvements

The following production hardening and architectural improvements are active in the current deployment:

- **Evaluation Runtime Isolation:** Remediated runtime settings mutation in `backend/evaluation/runner.py`. Benchmark evaluations now run within strict `try...finally` boundaries, and fake providers are strictly disabled in production (`settings.ENVIRONMENT == "production"`), preventing test runs from altering live chat providers.
- **Runtime Provider Diagnostics:** Implemented `GET /workspaces/{id}/evaluation/provider-status` and `POST /workspaces/{id}/evaluation/reset-providers` for transparent verification and administrative resetting of LLM and embedding states in memory.
- **Conversational & Overview Query Handling:** Integrated intent classification in `backend/app/services/intent_classifier.py` and calibrated `EvidenceSufficiencyGate` in `backend/app/rag/evidence_gate.py` to seamlessly route conversational messages and broad technical inquiries without false abstentions.
- **Dynamic AI Investigation Empty State:** Replaced static suggested questions with a clean, 3-pillar guidance empty state that encourages organic inquiries against ingested engineering documents.
- **Information Retrieval Metric Reformulation:** Implemented TREC-compliant Precision@K, Recall@K, MRR, and NDCG@K metrics in `backend/evaluation/metrics.py` with logarithmic rank discounting.
- **Evidence Gate Numerical Conflict Calibration:** Excluded incident IDs, dates, timestamps, and HTTP status codes from false-positive conflict detection, isolating conflicts to genuine metric contradictions.

---

## 11. Documentation Index

- [Architecture Specification](docs/architecture/SYSTEM_ARCHITECTURE.md)
- [Database Schema & Migrations](docs/database/DATABASE_SCHEMA.md)
- [API Documentation & Examples](docs/api/API_DOCUMENTATION.md)
- [AI Engineering Implementation Report](docs/reports/EIP_AI_ENGINEERING_IMPLEMENTATION_REPORT.md)
- [Evaluation Dataset & Metrics Report](docs/reports/EVALUATION_DATASET_AND_METRICS_REPORT.md)
- [Promptfoo Security Test Report](docs/reports/PROMPTFOO_SECURITY_TEST_REPORT.md)
- [Langfuse Observability Report](docs/reports/LANGFUSE_INSTRUMENTATION_REPORT.md)
- [LLM Usage Tracking Report](docs/reports/LLM_USAGE_TRACKING_REPORT.md)
- [Frontend Verification Report](docs/reports/FRONTEND_RUNTIME_VERIFICATION_REPORT.md)
- [Development Report](docs/reports/DEVELOPMENT_REPORT.md)
- [Demonstration Script](docs/DEMO_SCRIPT.md)
- [Final Assessment Submission Readiness Report](docs/reports/FINAL_ASSESSMENT_SUBMISSION_READINESS_REPORT.md)

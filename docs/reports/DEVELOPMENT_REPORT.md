# Engineering Intelligence Platform — Development Report

**Project:** Engineering Intelligence Platform (EIP)  
**Document Type:** Engineering Development & AI Tool Disclosure Report  
**Author:** AI Solutions Architect, Backend Engineer & Integration Lead  
**Date:** November 2026  
**Status:** Verification Complete — Release Candidate  

---

## 1. Executive Summary

This report documents the end-to-end engineering lifecycle of the **Engineering Intelligence Platform (EIP)**, a production-grade enterprise document intelligence and technical investigation system. The project was executed through an autonomous and collaborative software engineering process utilizing AI-assisted development tools under rigorous engineering supervision, automated testing, and independent quality audits.

In compliance with the technical assessment guidelines, this document provides complete disclosure of development phases, architectural trade-offs, AI tools utilized, tasks delegated, independent engineering decisions made, bugs identified and resolved, and an honest evaluation of verification boundaries.

---

## 2. Chronological Development Phases

```
+----------------------------------------------------------------------------------------------------+
|                                    PROJECT DEVELOPMENT PHASES                                      |
+---------+-----------------------------------------+------------------------------------------------+
| Phase   | Phase Title                             | Key Milestones & Deliverables                  |
+---------+-----------------------------------------+------------------------------------------------+
| Phase 1 | Scaffolding & Architecture Design       | PRD extraction, architecture specs, DDL design |
| Phase 2 | Core Backend Implementation             | FastAPI modular monolith, auth, parsers, RAG   |
| Phase 3 | Frontend Application Development        | React 18 / Vite / TypeScript SPA, Tailwind UI  |
| Phase 4 | Full-Stack Integration & QA             | Live API wiring, chunk explorer, conversation  |
| Phase 5 | Security Remediation & Hardening        | CORS validators, SECRET_KEY, Alembic migration |
| Phase 6 | RAG Quality, Evaluation & Observability | Evidence Gate, 46-Q dataset, Langfuse, Usage   |
| Phase 7 | Self-Review & Release Stabilization     | Terminology fixes, 149 pytest, build pass      |
+---------+-----------------------------------------+------------------------------------------------+
```

### Phase 1: Scaffolding & System Architecture Design
- Analyzed the business requirements document (`ENGINEERING INTELLIGENCE PLATFOR1.docx`).
- Formulated the System Architecture Specification (`docs/architecture/SYSTEM_ARCHITECTURE.md`) and Physical Database DDL (`docs/database/DATABASE_SCHEMA.md`).
- Authored initial Architecture Decision Records (ADRs 001 through 008) covering modular monolith boundaries, pgvector dual storage, hybrid search, and custom agent tool-calling.

### Phase 2: Core Backend Implementation
- Implemented the FastAPI modular monolith application (`backend/app/main.py`).
- Built authentication endpoints with JWT tokens and bcrypt password hashing.
- Developed document ingestion services supporting PDF (PyMuPDF / fitz), Markdown, CSV, and plain text.
- Implemented SHA-256 cryptographic deduplication.
- Created `VectorType` abstraction in SQLAlchemy/SQLModel supporting PostgreSQL `pgvector` HNSW index and SQLite JSON serialization.
- Engineered the custom autonomous `AgentOrchestrator` with three specialized tools: `Knowledge Base Search`, `Document Analysis`, and `Structured Report Generation`.
- Implemented conversational memory with sliding-window token budgeting.

### Phase 3: Frontend Application Development
- Initialized a modern React 18, Vite 5, and TypeScript single-page application.
- Built enterprise UI components using Tailwind CSS and Lucide React icons.
- Implemented full user workflows: Registration/Login, Document Management with upload dropzone and Chunk Explorer modal, Grounded Chat with interactive citation side drawers, Agent Studio with live step timeline visualizer, and Settings.

### Phase 4: Full-Stack Integration & Runtime Verification
- Replaced mocked client responses with real FastAPI backend integrations.
- Fixed conversation history persistence across page refreshes.
- Verified document processing lifecycle (`PENDING` -> `PROCESSING` -> `INDEXED`).
- Verified click-to-open citation inspection highlighting exact source document snippets.
- Removed silent fallback behaviors that concealed HTTP errors behind empty arrays.

### Phase 5: Security Remediation & Configuration Hardening
- Collaborated with OpenCode pairing agents to execute Phase 6 and Phase 8 security audits.
- Implemented strict production configuration validators in `backend/app/core/config.py`:
  - `SECRET_KEY` validator enforcing $\ge 32$ characters when `ENVIRONMENT=production`.
  - `CORS_ORIGINS` validator blocking wildcard `["*"]` in production environments.
- Secured API endpoints against unauthorized workspace data leakage via `verify_workspace_access()`.

### Phase 6: RAG Quality, Evaluation, Security Suite & Observability
- Implemented the `EvidenceSufficiencyGate` (`backend/app/rag/evidence_gate.py`):
  - Token coverage thresholding ($< 25\%$ coverage short-circuits to honest abstention without calling LLMs).
  - Triaged chunks into `PRIMARY` ($\ge 0.35$), `SUPPLEMENTARY` ($\ge 0.20$), and `IRRELEVANT` ($< 0.20$).
  - Filtered distractor documents and detected conflicting dates and numerical metrics across sources.
- Built active claim grounding verification (`verify_claim_grounding` in `backend/app/rag/grounding.py`) with prompt echo stripping.
- Created a 46-question golden evaluation dataset (`golden_evaluation_dataset.jsonl`) spanning 7 technical inquiry categories.
- Built an automated evaluation runner (`backend.evaluation.runner`) measuring deterministic context precision, recall, grounding rates, and abstention accuracy.
- Integrated Langfuse v5 tracing (`backend/app/observability/langfuse_tracer.py`) with `@observe` decorators and fail-safe local bypasses.
- Standardized single-entry LLM usage tracking (`LLMUsageEvent` schema and `llm_logs` table) with Alembic migration revision `58f1a23b49de`.
- Implemented promptfoo security test suite (`backend/tests/security/test_security_suite.py`) validating prompt injection defenses against `promptfooconfig.yaml`.

### Phase 7: Engineering Self-Review & Release Stabilization
- Executed an exhaustive 10-point self-review across all modified code and documentation.
- Corrected misleading evaluation terminology: clearly distinguished closed-form deterministic heuristic metrics from official LLM-judge RAGAS metrics.
- Explicitly documented that the 0.0000 hallucination rate is an offline benchmark result using `FakeLLMClient` and deterministic claim verification.
- Re-verified all 46 evaluation questions against synthetic fixtures, correcting 1 ground-truth context discrepancy (`q40`).
- Validated all test suites: 149/149 backend pytest tests passed, 10/10 frontend vitest tests passed, and frontend production build built cleanly in 6.23s.

---

## 3. Technical Decisions & Architectural Trade-offs

### 3.1 Custom Tool-Calling Agent vs. LangGraph
- **Decision:** Implemented an in-house, explicit tool-calling agent loop (`AgentOrchestrator`) rather than adopting LangGraph or CrewAI.
- **Rationale:**
  - Full architectural ownership: every step, prompt construction, and parameter parsing logic is explicit and transparent.
  - Zero opaque framework overhead: simplifies debugging and eliminates dependencies on rapidly churning third-party abstractions.
  - Resilience: strictly enforces step limits (max 5 iterations), parameter validation via Pydantic schemas, and timeout controls.
- **Trade-off:** Lacks out-of-the-box multi-agent graph branching, which was deemed unnecessary for the initial 3-tool investigation scope.

### 3.2 Unified PostgreSQL + pgvector vs. Dedicated Vector Store
- **Decision:** Utilized PostgreSQL 16 with the `pgvector` extension for combined relational and vector persistence.
- **Rationale:**
  - Eliminates dual-store synchronization bugs, two-phase commits, and distributed data drift.
  - Enables unified ACID transactions across document metadata, user access controls, and chunk embeddings.
  - Simplifies cloud operations: a single managed database instance (e.g. AWS RDS PostgreSQL) satisfies all storage requirements.
- **Trade-off:** In local development without PostgreSQL, custom `VectorType` fallback stores embeddings in SQLite as serialized JSON arrays.

### 3.3 Hybrid Dense + Sparse (BM25) Retrieval via Reciprocal Rank Fusion
- **Decision:** Implemented hybrid retrieval combining dense vector similarity with sparse BM25 lexical token matching, merged using Reciprocal Rank Fusion (RRF, $k=60$).
- **Rationale:**
  - Pure dense search frequently misses exact technical identifiers (e.g., error codes `504 Gateway Timeout`, table names `billing_events`, flag names `max_connections`).
  - Pure lexical search fails on semantic paraphrasing (e.g., "Postgres connection exhaustion" vs. "database pool saturation").
  - RRF provides rank-based score normalization without requiring delicate calibration of floating-point similarity thresholds.

### 3.4 Deterministic Evidence Gate & Verifier vs. Runtime LLM-as-a-Judge
- **Decision:** Built a pure-function mathematical evidence gate and claim grounding verifier rather than calling a second frontier LLM judge at runtime.
- **Rationale:**
  - Latency: Pure-function verification executes in $< 15\text{ ms}$, whereas a runtime LLM judge adds $1,500\text{--}3,000\text{ ms}$ of latency.
  - Financial Cost: Short-circuiting $< 25\%$ coverage queries saves $100\%$ of generation token costs on unanswerable/out-of-domain questions.
  - Determinism: Eliminates judge model non-determinism, stochastic drift, and prompt injection susceptibility.

### 3.5 Single-Entry Token Telemetry vs. Intermediate Retry Logging
- **Decision:** The `LLMFallbackRouter` logs exactly one record in `llm_logs` per completed user request, setting `is_fallback=True` if failover occurred.
- **Rationale:** Prevents artificial cost and token inflation in financial dashboards. Intermediate network or 429 failures are recorded as error traces in logs/Langfuse rather than multiplying billable usage records.

---

## 4. AI-Assisted Development Disclosure

In accordance with Section 7 (Assessment Rules) of the PRD specification, all AI tools and automated assistance utilized during this project are cataloged below:

| AI Tool / Environment | Model Used | Tasks Delegated & Role | Human / Lead Review & Control |
| :--- | :--- | :--- | :--- |
| **Antigravity IDE** | Claude 3.5 Sonnet / Gemini | High-level architectural planning, test harness creation, code refactoring, and documentation drafting. | Architecture, design decisions, and final code reviews directed by the technical lead. |
| **OpenCode Pairing Agent 1** | Claude 3.5 Sonnet | Backend code implementation and security remediation (Phase 5/6). | Code diffs inspected and validated via automated pytest test suites. |
| **OpenCode Pairing Agent 2** | Claude 3.5 Sonnet | Independent read-only QA audit, route verification, and metric cross-checking. | Findings reviewed and addressed during Phase 7 self-review. |

### Engineering Decisions Made Independently
1. Selection of modular monolith structure with FastAPI over microservices.
2. Formulation of the `EvidenceSufficiencyGate` algorithm and coverage heuristics.
3. Architecture of single-entry accounting in `LLMFallbackRouter`.
4. Construction of the 46-question golden evaluation dataset with ground-truth fixture excerpts.
5. Implementation of prompt echo stripping in claim grounding verification.

---

## 5. Implementation Status Breakdown

### 5.1 Completed & Verified Capabilities
- [x] Multi-format document ingestion (PDF via PyMuPDF, Markdown, CSV, TXT).
- [x] Cryptographic SHA-256 deduplication and workspace isolation.
- [x] Semantic chunking with overlap boundaries and 1536d vector generation.
- [x] Hybrid retrieval (Dense `pgvector` + Sparse BM25 + Reciprocal Rank Fusion).
- [x] RAG Evidence Sufficiency Gate ($< 25\%$ coverage short-circuit to abstention; chunk triage; date/numerical conflict detection).
- [x] Active claim grounding verifier and prompt echo filter.
- [x] Multi-provider LLM fallback router (Claude 3.5 Sonnet primary, GPT-4o fallback, FakeLLMClient test mode).
- [x] Autonomous agent coordinating 3 functional tools (Search, Analyze, Report) with loop limits and parameter validation.
- [x] Multi-turn conversational memory with sliding-window token management.
- [x] Responsive React 18 / Vite 5 / TypeScript dashboard with Tailwind CSS.
- [x] 46-question golden evaluation benchmark runner and live API endpoints.
- [x] Langfuse v5 request tracing with fail-safe local fallback.
- [x] Standardized single-entry LLM usage telemetry and Alembic migration `58f1a23b49de`.
- [x] Full test coverage: 149 backend pytest tests passing; 10 frontend vitest tests passing; frontend production build passing in 6.23s.

### 5.2 Partially Completed / In Progress
- [ ] **Document OCR:** Scanned image-only PDFs currently extract empty text via PyMuPDF; requires an upstream OCR pipeline (e.g. Tesseract / AWS Textract). Digital PDFs, Markdown, CSV, and TXT are fully functional.
- [ ] **Persistent Evaluation Results DB:** Evaluation runs currently execute and return real results dynamically via API, but historic evaluation runs are not stored in a separate relational evaluation table.

### 5.3 Future Work (Production Roadmap)
- [ ] Distributed Celery / ARQ background worker fleet with Redis message broker.
- [ ] AWS S3 object storage with server-side KMS encryption and presigned upload URLs.
- [ ] Dedicated cross-encoder neural reranking microservice running on GPU infrastructure.
- [ ] Multi-agent collaboration with human-in-the-loop review for infrastructure modifications.

---

## 6. Deployment & Verification Disclosure

To prevent misrepresentation:
- **Local & Docker Verification:** The platform has been thoroughly tested and verified in local development environments (Python 3.14 on Windows/Linux) and multi-container Docker environments (`docker-compose.yml`).
- **Cloud Hosting Status:** The code is architected to be cloud-ready (stateless API server, portable `VectorType`, environment-injected secrets). However, **live public cloud URLs (e.g. AWS ECS / Render / Vercel) require user-managed cloud account provisioning, DNS configuration, and active external API billing keys**.
- **Metrics Attribution:** All evaluation metrics reported in this repository are derived from automated execution of the 46-question golden benchmark runner using deterministic local verification modes.


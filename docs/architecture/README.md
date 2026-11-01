# Architecture Documentation (`docs/architecture/`)

## 1. Overview
This directory contains the complete technical architecture design, editable diagrams, decision records, and implementation roadmap for the **Engineering Intelligence Platform**. It serves as the primary architectural blueprint for implementation and the formal architecture deliverable required by the technical assessment.

---

## 2. Directory Contents & Artifact Guide

### Core Architecture Specifications
- **[`SYSTEM_ARCHITECTURE.md`](SYSTEM_ARCHITECTURE.md):**
  - The comprehensive technical architecture document covering all architectural tiers: Frontend (React/Vite/TS), Modular Monolith Backend (FastAPI), Document Intelligence (PyMuPDF), Advanced Hybrid RAG (pgvector + BM25 + Reranking), Multi-Provider LLM Fallback (Claude + OpenAI), Controlled Autonomous AI Agent, Conversational Memory, Security & Prompt Injection Defense, Redis Background Processing, Evaluation Harness (RAGAS), and Cloud Deployment.
  - Includes full entity schemas, resilience matrices, and the requirement-to-architecture traceability table.

- **[`IMPLEMENTATION_ROADMAP.md`](IMPLEMENTATION_ROADMAP.md):**
  - The phased engineering plan breaking development into six logical, dependency-ordered phases.
  - Outlines the critical path, early integration testing gates, technical risk registry, and live technical verification preparedness.

---

### Visual Architecture Diagrams
- **Main System Architecture Diagram:**
  - **Rendered Image:** [`system_architecture.png`](system_architecture.png) (High-resolution visual architecture diagram showing frontend, backend, database, vectors, queues, AI providers, and cloud boundaries).
  - **Editable Source:** [`system_architecture.mmd`](system_architecture.mmd) (Mermaid flowchart source code).
- **Data Flow Diagram:**
  - **Rendered Image:** [`data_flow.png`](data_flow.png) (Sequence flow illustrating Flow 1: Asynchronous Document Ingestion and Flow 2: Grounded RAG Query Execution).
  - **Editable Source:** [`data_flow.mmd`](data_flow.mmd) (Mermaid sequence diagram source code).

---

### Architecture Decision Records (`decisions/`)
Standalone ADR files documenting the context, decisions, alternatives considered, rationales, and consequences for foundational architectural choices:

1. **[`ADR-001: Modular Monolith Backend Architecture`](decisions/ADR-001-modular-monolith-backend.md)** — Decision to build a Python/FastAPI modular monolith over distributed microservices.
2. **[`ADR-002: PostgreSQL with pgvector for Unified Relational and Vector Storage`](decisions/ADR-002-postgresql-pgvector-dual-storage.md)** — Decision to use PostgreSQL 16 + `pgvector` to eliminate dual-store synchronization bugs.
3. **[`ADR-003: Hybrid Retrieval with Reciprocal Rank Fusion and Cross-Encoder Reranking`](decisions/ADR-003-hybrid-retrieval-and-reranking.md)** — Decision to merge dense semantic search with sparse BM25 lexical search and neural reranking for technical accuracy.
4. **[`ADR-004: Custom Tool-Calling Agent Architecture`](decisions/ADR-004-custom-tool-calling-agent.md)** — Decision to build a transparent custom agent runtime over opaque LangChain/LangGraph abstractions.
5. **[`ADR-005: Multi-Provider LLM Abstraction and Intelligent Circuit-Breaker Fallback`](decisions/ADR-005-multi-provider-llm-fallback.md)** — Decision to implement provider failover from Claude 3.5 Sonnet to OpenAI GPT-4o on rate limits or outages.
6. **[`ADR-006: Asynchronous Document Processing with Redis Task Queue`](decisions/ADR-006-asynchronous-document-processing.md)** — Decision to use Redis and background workers to prevent reverse-proxy HTTP gateway timeouts.
7. **[`ADR-007: Practical Cloud Deployment and Infrastructure Strategy`](decisions/ADR-007-cloud-deployment-strategy.md)** — Decision to use managed container infrastructure (AWS App Runner / RDS / ElastiCache) rather than overengineered Kubernetes.
8. **[`ADR-008: Document Access Model and Knowledge Base Organization`](decisions/ADR-008-document-access-and-knowledge-organization.md)** — Analysis and recommended defaults for workspace-shared document access and unified metadata-scoped knowledge bases (pending product confirmation).

---

## 3. Maintenance & Diagram Updates
When modifying system components or data flows:
1. Update the editable `.mmd` source files first.
2. Re-render the corresponding `.png` files via Kroki or Mermaid CLI.
3. Update the corresponding sections in `SYSTEM_ARCHITECTURE.md` and relevant ADRs.


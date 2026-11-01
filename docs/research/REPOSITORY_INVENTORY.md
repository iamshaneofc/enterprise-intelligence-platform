# Reference Repository Inventory
## Engineering Intelligence Platform — Research & Audit Phase
**Document Type:** Technical Repository Inventory & Provenance Record  
**Version:** 1.0  
**Audit Date:** November 1, 2026  
**Auditor:** Senior AI Solutions Architect & Technical Auditor  
**Status:** Completed & Verified  

---

## 1. Overview
As part of the technical research phase for the **Engineering Intelligence Platform**, three public reference repositories representing different architectural approaches to RAG, document intelligence, and AI agents were cloned into the isolated `reference_repos/` directory.

This document records the exact provenance, Git commit metadata, licensing, directory topologies, and inspection statuses for all three reference codebases.

---

## 2. Summary Comparison Table

| Metric / Attribute | Repository 1: `agent-doc-intelligence` | Repository 2: `RAG-Enterprise` | Repository 3: `enterprise-knowledge-assistant` |
| :--- | :--- | :--- | :--- |
| **GitHub URL** | `https://github.com/LeonxLJX/agent-doc-intelligence.git` | `https://github.com/sohrab-phd/RAG-Enterprise.git` | `https://github.com/daniella-mv/enterprise-knowledge-assistant.git` |
| **Local Clone Path** | `reference_repos/agent-doc-intelligence/` | `reference_repos/RAG-Enterprise/` | `reference_repos/enterprise-knowledge-assistant/` |
| **Current Branch** | `main` | `main` | `main` |
| **Commit Hash** | `712d7c193c9085d335872e2e6b4b5632c94d5357` | `fe6a2bf197d5f3ac7412b668d5d2cb959acaaef0` | `fa56977e32f9a9afab8d1dfa83dd4b303fc30da0` |
| **Commit Date** | `2026-09-21 18:39:46 +0800` | `2026-08-06 18:33:57 +0330` | `2026-05-25 22:15:02 -0400` |
| **Total Commits** | 2 commits | 83 commits | 6 commits |
| **Primary Author** | LeonxLJX | Sohrab Pirhadi | daniella-mv |
| **License** | MIT License | MIT License | Apache-2.0 License |
| **Codebase Size** | 34 Python, 9 TS/TSX files (~45 total) | 360 Python, 93 TS/TSX files (~600 total) | 58 Python, 9 TS/TSX files (~80 total) |
| **Primary Architectural Focus** | LangGraph Agent State Machine, Tracing & Evaluation | Enterprise Knowledge Management, Anti-Hallucination, Grounding | Production RAG on pgvector, Citation Mapping, 20-Q Evaluation |
| **Inspection Status** | Complete static inspection & file audit | Complete static inspection & file audit | Complete static inspection & file audit |

---

## 3. Individual Repository Profiles

### 3.1 Repository 1: `agent-doc-intelligence`
- **Origin & Purpose:** A prototype exploring agentic document intelligence, multi-tool execution, LangGraph state management, and comparative RAG evaluation.
- **Git Metadata:**
  - *Branch:* `main`
  - *Latest Commit:* `712d7c193c9085d335872e2e6b4b5632c94d5357`
  - *Commit Message:* `feat: add LangSmith tracing and comprehensive RAG evaluation with LLM-as-judge and A/B testing`
  - *License:* MIT License
- **Key Modules Inspected:**
  - `backend/app/agent/graph.py` (LangGraph state machine: `START -> retrieve -> plan -> execute_tools -> answer -> END`)
  - `backend/app/agent/tools.py` (Tool registry with graceful error handling: `{"ok": false, "error": ...}`)
  - `backend/app/core/retriever.py` (In-memory BM25 tokenizer + Reciprocal Rank Fusion)
  - `backend/app/core/vector_store.py` (Zero-dependency `InMemoryStore` using NumPy cosine similarity and pluggable `ChromaStore`)
  - `backend/app/eval/llm_judge.py` & `metrics.py` (Self-contained RAGAS-style LLM judge and lexical metrics)
  - `backend/configs/` (`baseline.yaml`, `dense_heavy.yaml`, `keyword_heavy.yaml` A/B configurations)
- **Architectural Gaps Identified:**
  - Zero relational database integration (no PostgreSQL, no Alembic).
  - Zero user authentication or multi-tenant workspace isolation.
  - Zero persistent document versioning or citation mapping tables.

```text
agent-doc-intelligence/
├── backend/
│   ├── app/
│   │   ├── agent/         # LangGraph state, tools registry, planner
│   │   ├── api/           # FastAPI endpoints
│   │   ├── core/          # Document parsers, chunker, retriever, vector store
│   │   └── eval/          # Benchmark dataset, LLM judge, RAG metrics
│   ├── configs/           # A/B testing retrieval parameter YAMLs
│   └── tests/             # Pytest unit tests for agent, chunker, retriever
└── frontend/
    └── src/
        ├── api/           # API client
        └── components/    # ChatPanel, SummaryCard, TraceViewer, UploadZone
```

---

### 3.2 Repository 2: `RAG-Enterprise`
- **Origin & Purpose:** A heavily engineered enterprise knowledge management system with strict anti-hallucination policies, domain-driven structure, and exhaustive specification documents.
- **Git Metadata:**
  - *Branch:* `main`
  - *Latest Commit:* `fe6a2bf197d5f3ac7412b668d5d2cb959acaaef0`
  - *Commit Message:* `Delete tools/generate_documentation_docx.py`
  - *License:* MIT License
- **Key Modules Inspected:**
  - `backend/src/rag_enterprise/generation/citations.py` (`is_model_abstention` regex parsing)
  - `backend/src/rag_enterprise/generation/grounding.py` (Deterministic verification: `strip_evidence_echo`, `find_ungrounded_claims` checking digits and URLs, `find_unsupported_entities`)
  - `backend/src/rag_enterprise/retrieval/hybrid.py` (Reciprocal Rank Fusion with $k=60$)
  - `backend/src/rag_enterprise/retrieval/ranking.py` (Calibrated heuristic ranking deltas on top of cosine similarity)
  - `backend/src/rag_enterprise/db/mixins/` (`tenant.py`, `soft_delete.py`, `versioning.py`, `audit.py`)
  - `specs/` (Exhaustive spec markdown files for Features 001 through 008)
- **Architectural Gaps Identified:**
  - Explicit non-goal: No AI agent, no tool execution, no function calling.
  - No conversational memory summarization or long-term session pruning.
  - Significant architectural density: CQRS commands, event dispatchers, and multiple abstraction layers that exceed the needs of a single-developer project.

```text
RAG-Enterprise/
├── backend/
│   ├── alembic/           # Database migration versions
│   └── src/rag_enterprise/
│       ├── api/           # FastAPI routes & middleware
│       ├── application/   # CQRS command/query handlers & DTOs
│       ├── chunking/      # Text splitters
│       ├── db/            # SQLAlchemy models, mixins (tenant, soft_delete)
│       ├── generation/    # Prompt builder, citations, grounding guards
│       ├── indexing/      # BGE-M3 embeddings & chunk repositories
│       ├── knowledge/     # Knowledge base, document, version repositories
│       └── retrieval/     # BM25, hybrid fusion, ranking calibration
├── specs/                 # Features 001 to 008 formal specifications
├── tools/                 # Benchmark runners & regression test suites
└── frontend/              # React 18 / Tailwind client
```

---

### 3.3 Repository 3: `enterprise-knowledge-assistant`
- **Origin & Purpose:** A production-styled enterprise assistant built on FastAPI, PostgreSQL (`pgvector`), AWS Bedrock, and a React frontend, featuring a strict 20-question golden evaluation suite.
- **Git Metadata:**
  - *Branch:* `main`
  - *Latest Commit:* `fa56977e32f9a9afab8d1dfa83dd4b303fc30da0`
  - *Commit Message:* `Remove duplicate baseline eval run`
  - *License:* Apache-2.0 License
- **Key Modules Inspected:**
  - `backend/app/services/generation.py` (`build_rag_prompt` aliasing chunks as `[c_0]`, `[c_1]` via `CitationMap`)
  - `backend/app/services/retrieval.py` (Hybrid search combining pgvector cosine similarity and `tsvector` BM25 full-text via RRF)
  - `backend/app/models/chunk.py` (Denormalized `owner_id` to eliminate table joins during vector search)
  - `evals/datasets/golden_qa.jsonl` (Hand-curated 20-question benchmark with `expected_to_abstain` flags)
  - `evals/eval_lib.py` & `run_eval.py` (Automated CLI runner generating markdown evaluation reports)
  - `frontend/src/` (Clean, focused React + Tailwind UI with streaming SSE and interactive citations)
- **Architectural Gaps Identified:**
  - No AI agent or tool-calling runtime.
  - Hardcoded `local-user` authentication (no JWT, no user registration).
  - Hardcoded to AWS Bedrock Titan / Claude (lacks multi-provider fallback between OpenAI and Anthropic).

```text
enterprise-knowledge-assistant/
├── backend/
│   ├── alembic/           # PostgreSQL migrations
│   ├── app/
│   │   ├── adapters/      # Bedrock, pgvector DB, embeddings, MinIO storage
│   │   ├── api/routes/    # chat.py, documents.py, health.py
│   │   ├── models/        # document.py, chunk.py (pgvector Vector(1024))
│   │   └── services/      # chunker, generation, ingestion, parser, retrieval
│   └── Dockerfile
├── evals/
│   ├── datasets/          # golden_qa.jsonl (20 questions with ground truth)
│   ├── eval_lib.py        # Metrics: answered, abstained_correctly, keyword_recall
│   ├── reports/           # Markdown timestamped evaluation reports
│   └── run_eval.py        # Automated SSE evaluation runner
├── frontend/              # React, TypeScript, Tailwind SPA
├── sample_docs/           # employee_handbook.md, helpdesk_sop.md, it_security_policy.md
└── docker-compose.yml     # Local orchestration of API, Frontend, Postgres, MinIO
```

---

## 4. Integrity Confirmation
- All three repositories were cloned using standard Git protocols into isolated subdirectories under `reference_repos/`.
- No files from these repositories were moved, copied, or imported into our actual platform workspace (`backend/`, `frontend/`, `docs/architecture/`, `docs/database/`).
- Original Git history, branches, and commit hashes remain completely intact.


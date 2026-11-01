# Technology Stack Comparative Audit
## Engineering Intelligence Platform
**Document Type:** Evidence-Based Technology Comparison & Recommendation Analysis  
**Version:** 1.0  
**Phase:** Technical Research & Stack Evaluation  
**Status:** Completed (Proposals Awaiting Step 4 Confirmation)  

---

## 1. Overview
This report evaluates the technology selections across the three audited reference repositories (`agent-doc-intelligence`, `RAG-Enterprise`, `enterprise-knowledge-assistant`) and compares them directly against the technology stack planned for the **Engineering Intelligence Platform**.

Each major layer is evaluated based on concrete source-code evidence, operational trade-offs, and fitness for the AI Engineer Advanced Technical Assessment.

---

## 2. Technology Evaluation Matrix

```
+-------------------------------------------------------------------------------------------------------------------------+
|                                              TECHNOLOGY STACK COMPARATIVE MATRIX                                        |
+--------------------------+---------------------------+---------------------------+---------------------------+----------+
| Technology Area          | `agent-doc-intelligence`  | `RAG-Enterprise`          | `enterprise-assistant`    | Our Rec. |
+--------------------------+---------------------------+---------------------------+---------------------------+----------+
| Backend Framework        | FastAPI 0.115             | FastAPI 0.115             | FastAPI 0.115             | ADOPT    |
| Schema Validation        | Pydantic v2               | Pydantic v2               | Pydantic v2               | ADOPT    |
| Relational ORM           | None (In-Memory)          | SQLAlchemy 2.0 + Alembic  | SQLAlchemy 2.0 + Alembic  | ADOPT    |
| Vector Storage           | In-Memory NumPy / Chroma  | PostgreSQL + pgvector     | PostgreSQL + pgvector     | ADOPT    |
| Lexical / BM25 Search    | In-Memory Python BM25     | Custom BM25 Index         | Postgres tsvector / GIN   | ADOPT    |
| Rank Fusion              | RRF (k=60)                | RRF (k=60) + Diagnostics  | RRF (k=60)                | ADOPT    |
| Document Parsers         | pypdf, python-docx, bs4   | PyPDF, docx, markdown     | PyMuPDF (fitz)            | ADOPT    |
| Primary LLM Routing      | Mock / OpenAI Direct      | Local / Ollama / OpenAI   | AWS Bedrock (Claude)      | ADOPT    |
| Fallback Resilience      | None                      | None                      | None                      | ADOPT    |
| Agent Framework          | LangGraph 0.2             | None (Explicit non-goal)  | None                      | AVOID    |
| Agent Architecture       | StateGraph + ToolRegistry | None                      | None                      | CUSTOM   |
| Citation Mechanism       | Bracketed [DocID]         | Regex [1..N] Markers      | Short Aliasing [c_0..N]   | ADOPT    |
| Grounding Verification   | LLM-as-a-Judge            | Deterministic Regex/Digit | String Keyword Overlap    | ADOPT    |
| Evaluation Harness       | LLM Judge + Lexical       | Regression Benchmark Suite| 20-Q Golden Dataset + CLI | ADOPT    |
| Observability            | LangSmith + JSONL         | Custom JSON Logger        | Custom Loguru Logger      | ADOPT    |
| Background Jobs          | None (In-request)         | Async Pipeline            | None (In-request)         | ADOPT    |
| Frontend Client          | React / Vite (Basic)      | React 18 / Tailwind       | React 18 / Tailwind       | ADOPT    |
| Containerization         | Dockerfile                | Docker Compose (Multi)    | Docker Compose (Full)     | ADOPT    |
+--------------------------+---------------------------+---------------------------+---------------------------+----------+
```

---

## 3. Deep-Dive Technology Evaluations

### 3.1 Backend & ORM: FastAPI + Pydantic v2 + SQLAlchemy 2.0
- **Reference Evidence:**
  - `agent-doc-intelligence`: Uses FastAPI 0.115 and Pydantic v2, but no ORM.
  - `RAG-Enterprise`: Extensive SQLAlchemy 2.0 mapped columns and Alembic migrations (`backend/src/rag_enterprise/db/`).
  - `enterprise-knowledge-assistant`: Clean, idiomatic SQLAlchemy 2.0 using `Mapped` and `mapped_column` (`backend/app/models/`).
- **Problem Solved:** Asynchronous ASGI request handling, automatic OpenAPI/Swagger documentation, type-safe request/response DTO validation, and robust relational persistence.
- **Trade-offs:** SQLAlchemy async sessions require careful transaction boundary handling (`async with session.begin():`).
- **Recommendation:** **ADOPT**. Universal standard across all three repositories.

---

### 3.2 Vector & Hybrid Database: PostgreSQL 16 + `pgvector`
- **Reference Evidence:**
  - `enterprise-knowledge-assistant`: Uses `pgvector.sqlalchemy.Vector(1024)` in `backend/app/models/chunk.py` with cosine similarity (`<=>`) and PostgreSQL `tsvector` generated columns for BM25 full-text search.
  - `RAG-Enterprise`: Uses `pgvector` with BGE-M3 dense vectors.
  - `agent-doc-intelligence`: Lacks persistent vector storage (uses in-memory NumPy array).
- **Problem Solved:** Eliminates dual-store split-brain synchronization bugs between relational metadata and vector embeddings; supports ACID transactions on chunk deletion.
- **Trade-offs:** Slightly more RAM-intensive than specialized serverless vector stores (e.g., Pinecone); requires PostgreSQL with `pgvector` extension compiled.
- **Recommendation:** **ADOPT**. Unifying vector and relational state in PostgreSQL is heavily validated by `RAG-Enterprise` and `enterprise-knowledge-assistant`.

---

### 3.3 Lexical Search: PostgreSQL `tsvector` vs. Pure-Python BM25
- **Reference Evidence:**
  - `enterprise-knowledge-assistant`: Employs native PostgreSQL `tsvector` stored generated columns with GIN indexes (`to_tsvector('english', content)`).
  - `agent-doc-intelligence`: Implements an in-memory `BM25` class in pure Python (`app/core/retriever.py`, lines 14–48).
  - `RAG-Enterprise`: Maintains an in-memory inverted BM25 index serialized alongside the database.
- **Comparison & Trade-offs:**
  - In-memory BM25 indexes require loading all document tokens into web process RAM, risking Out-Of-Memory (OOM) crashes on large multi-megabyte corpora.
  - PostgreSQL `tsvector` GIN indexing executes directly inside the database engine, scales to millions of rows, leverages database buffer caches, and enables combined SQL filtering in a single query.
- **Recommendation:** **ADOPT PostgreSQL `tsvector` + GIN indexing** for production storage, while retaining pure-Python BM25 as an offline test fixture.

---

### 3.4 Citation Architecture: Short Aliasing (`[c_0]`, `[c_1]`) vs. UUID Markers
- **Reference Evidence:**
  - `enterprise-knowledge-assistant`: In `backend/app/services/generation.py`, aliases retrieved chunks as `[c_0]`, `[c_1]`, `[c_2]` in the prompt and resolves them via a `CitationMap`.
  - `RAG-Enterprise`: Numbered markers `[1]`, `[2]` mapped back to evidence array indices.
  - `agent-doc-intelligence`: Asks the model to repeat document filenames in prose.
- **Problem Solved:** LLMs frequently truncate, hallucinate, or mistype long 36-character UUIDs (`[chunk_id=9f12d8a0-...]`). Short aliases (`[c_0]`) are token-efficient (1-2 tokens), unambiguous, and can be reliably extracted via regex `\[(c_\d+)\]`.
- **Recommendation:** **ADOPT Short Aliasing (`[c_0]`, `[c_1]`) with `CitationMap`**. This is one of the highest-value engineering patterns discovered in the audit.

---

### 3.5 Anti-Hallucination & Grounding: Deterministic Guards vs. LLM Evaluators
- **Reference Evidence:**
  - `RAG-Enterprise`: Implements `find_ungrounded_claims` in `generation/grounding.py` (lines 42–85) verifying that every number, date, and URL in the answer literally appears in the source chunks. If an ungrounded number is detected, the answer is replaced with an abstention!
  - `agent-doc-intelligence`: Uses a secondary LLM call (`llm_judge.py`) to grade faithfulness.
- **Comparison & Trade-offs:**
  - LLM-as-a-judge incurs latency (1-2 seconds) and API token costs ($0.01 per question) on every user chat request.
  - Deterministic regex checking executes in **< 1 millisecond** with zero token cost, catching the most dangerous failure modes in engineering runbooks (invented port numbers, wrong error codes, fake URLs).
- **Recommendation:** **ADOPT BOTH**. Use deterministic regex checking as an inline gatekeeper on live chat queries, and reserve LLM-as-a-judge for offline benchmark runs.

---

### 3.6 Agent Framework: Custom Tool-Calling Engine vs. LangGraph
- **Reference Evidence:**
  - `agent-doc-intelligence`: Uses `langgraph>=0.2` with `StateGraph(AgentState)` (`app/agent/graph.py`).
  - `RAG-Enterprise` & `enterprise-knowledge-assistant`: Zero agent implementations.
- **Analysis:**
  - `agent-doc-intelligence`'s LangGraph implementation works well, but pulls in `langchain-core`, `langchain-community`, and complex internal graph transitions.
  - LangChain ecosystem packages undergo frequent breaking API changes across minor version bumps.
  - In a 60-minute supervised technical verification where the candidate must modify an agent tool live, an opaque graph engine creates unnecessary debugging friction.
- **Recommendation:** **AVOID LangGraph; BUILD Custom Tool-Calling Engine** ([ADR-004](file:///z:/enterprise-intelligence-platform/docs/architecture/decisions/ADR-004-custom-tool-calling-agent.md)). Writing the 5-step loop in ~150 lines of typed Python using Pydantic schemas provides complete transparency, zero black-box overhead, and maximum explainability.

---

### 3.7 Evaluation Framework: 20-Question Golden Benchmark + CLI Runner
- **Reference Evidence:**
  - `enterprise-knowledge-assistant`: Curated `golden_qa.jsonl` (20 questions with ground truth keywords and `expected_to_abstain: true` flags) and an automated CLI runner (`run_eval.py`).
  - `agent-doc-intelligence`: Self-contained LLM judge (`llm_judge.py`) and comparative A/B configuration testing (`--compare configs/baseline.yaml configs/dense_heavy.yaml`).
- **Recommendation:** **ADOPT HYBRID EVALUATION HARNESS**. Combine the 20-question `golden_qa.jsonl` dataset structure from `enterprise-knowledge-assistant` with the self-contained LLM judge prompts from `agent-doc-intelligence`. This satisfies Module G completely without depending on heavy third-party evaluation SaaS.

---

### 3.8 Document Processing: PyMuPDF (`fitz`) vs. `pypdf`
- **Reference Evidence:**
  - `enterprise-knowledge-assistant`: Uses PyMuPDF (`fitz`) for PDF text and page-number extraction (`app/services/parser.py`).
  - `agent-doc-intelligence`: Uses `pypdf` (`app/core/document_parser.py`).
- **Comparison & Trade-offs:**
  - PyMuPDF is implemented in C (MuPDF library), executing **10x to 25x faster** than pure-Python `pypdf`, while accurately extracting multi-column layouts and tabular postmortem data.
- **Recommendation:** **ADOPT PyMuPDF (`fitz`)** for PDF extraction, supplemented by native Python `csv` and `markdown` parsers.


# Engineering Intelligence Platform — Technology Adoption Audit
**Comprehensive AI Engineering Stack Evaluation**  
**Author:** Senior AI Systems Architect & Technology Evaluation Engineer  
**Date:** November 2026  
**Document Status:** Complete Architecture Audit & Strategic Technology Assessment  
**Mode:** READ-ONLY ARCHITECTURAL AUDIT  

---

## 1. Objective & Audit Methodology

The Engineering Intelligence Platform (EIP) is an enterprise document intelligence and investigation system designed for Software Engineers, SREs, and DevOps teams.

This audit evaluates candidate AI engineering technologies against EIP’s existing architecture to establish:
- What capabilities we already have.
- What capabilities are missing or fragile.
- Which technologies genuinely improve our architecture without adding unnecessary complexity.
- Which technologies overlap with or duplicate existing implementations.
- Which should be adopted immediately (`ADOPT NOW`), scheduled for subsequent releases (`ADOPT LATER`), kept as custom code (`KEEP CUSTOM IMPLEMENTATION`), prototyped (`RUN A PROOF OF CONCEPT`), or rejected (`REJECT / UNNECESSARY`).

### Audit Principles
1. **Evidence Over Popularity:** Technologies are evaluated on technical fit, deterministic behavior, latency, cost, and reliability—not GitHub stars or marketing hype.
2. **Preserve What Works:** EIP already possesses a robust foundation in PostgreSQL 16 + `pgvector`, FastAPI, Pydantic v2 schemas, and primary-to-fallback LLM routing. We do not replace working code without clear empirical justification.
3. **Strict Non-Destructive Audit:** Conducted entirely in read-only mode with zero changes to application code, database schemas, or dependencies.

---

## 2. Deep Technology Evaluations

### 2.1 A. LangGraph vs. EIP Custom Agent
*Detailed architectural comparison is provided in [`docs/research/LANGGRAPH_VS_CUSTOM_AGENT_COMPARISON.md`](file:///z:/enterprise-intelligence-platform/docs/research/LANGGRAPH_VS_CUSTOM_AGENT_COMPARISON.md).*

#### Current EIP Implementation
- **Files:** [`backend/app/agents/orchestrator.py`](file:///z:/enterprise-intelligence-platform/backend/app/agents/orchestrator.py) (453 LOC), [`backend/app/agents/tools.py`](file:///z:/enterprise-intelligence-platform/backend/app/agents/tools.py) (188 LOC), [`backend/app/models/agent.py`](file:///z:/enterprise-intelligence-platform/backend/app/models/agent.py) (90 LOC).
- **Architecture:** Procedural ReAct loop running up to `AGENT_MAX_STEPS = 5` iterations. It uses thread-based timeout enforcement, robust regex/JSON action parsing with default fallbacks, prompt injection sanitization on tool outputs, and synchronous relational logging of tool executions into PostgreSQL.
- **Tools:** Trio of incident tools (`knowledge_base_search`, `document_analysis`, `structured_report_generation`) validated via Pydantic schemas.

#### Candidate Technology: LangGraph (OSS v0.2+)
- **Core Capabilities:** Explicit state graphs (`StateGraph`), state reducers, checkpointing backed by PostgreSQL, native streaming of node events/tokens, async execution, and human-in-the-loop interruption (`interrupt_before`).
- **Can it be used without full LangChain?** **YES.** LangGraph is an independent package requiring only Python typing, Pydantic, and callable node functions.
- **Can we retain our existing tools, schemas, and provider router?** **YES.** EIP's existing tool functions and `llm_router.generate()` can be invoked directly inside LangGraph nodes.

#### Architectural Verdict
- **Classification: RUN A PROOF OF CONCEPT / ADOPT LATER (Phase 2).**
- **Justification:** EIP's custom agent executes its current 5-step incident investigation loop reliably with zero framework overhead and robust security sanitization. Migrating to LangGraph does not fix the urgent evaluation gaps (which stem from RAG retrieval and evidence sufficiency, not agent loop execution). However, LangGraph's support for streaming and human-in-the-loop review makes it the ideal foundation for Phase 2 incident investigation workflows.

---

### 2.2 B. Langfuse — Observability and Distributed Tracing
*Detailed design is provided in [`docs/research/AI_OBSERVABILITY_AND_EVALUATION_DESIGN.md`](file:///z:/enterprise-intelligence-platform/docs/research/AI_OBSERVABILITY_AND_EVALUATION_DESIGN.md).*

#### Current EIP Implementation
- **Files:** [`backend/app/models/llm_log.py`](file:///z:/enterprise-intelligence-platform/backend/app/models/llm_log.py), [`backend/app/llm/router.py` L137–L161](file:///z:/enterprise-intelligence-platform/backend/app/llm/router.py#L137-L161).
- **Architecture:** Synchronous database insertion of `LLMLog` recording `provider`, `model`, `prompt_tokens`, `completion_tokens`, `latency_ms`, and `cost_usd` calculated via static dictionary lookup.
- **Gaps:** Flat logging without span hierarchy (no linking of search $\rightarrow$ rerank $\rightarrow$ generation), no prompt cache token accounting, and no correlation between offline evaluation scores and production traces.

#### Candidate Technology: Langfuse (SDK v2.x)
- **Core Capabilities:** Distributed LLM tracing, nested spans, dynamic model pricing engine, session/conversation association, user/workspace attribution, OpenTelemetry compliance, self-hosted deployment via Docker Compose.
- **Current SDK Standard:** Uses modern `@observe()` decorator with zero-overhead background async batching; avoids deprecated v1 callback handlers.
- **Privacy Compliance:** Self-hosted deployment keeps all engineering documentation, prompts, and database metadata within the customer's private VPC.

#### Architectural Verdict
- **Classification: ADOPT NOW (Phase 1).**
- **Justification:** Self-hosted Langfuse directly solves EIP's observability deficit without altering application-level data contracts. Our existing PostgreSQL `llm_logs` table remains the authoritative relational billing record, while Langfuse provides distributed spans, latency waterfalls, and prompt debugging.

---

### 2.3 C. RAGAS — Automated RAG Quality Evaluation
*Detailed design is provided in [`docs/research/AI_OBSERVABILITY_AND_EVALUATION_DESIGN.md`](file:///z:/enterprise-intelligence-platform/docs/research/AI_OBSERVABILITY_AND_EVALUATION_DESIGN.md).*

#### Current EIP Implementation
- **Files:** [`backend/evaluation/metrics.py`](file:///z:/enterprise-intelligence-platform/backend/evaluation/metrics.py), [`backend/evaluation/runner.py`](file:///z:/enterprise-intelligence-platform/backend/evaluation/runner.py), [`backend/tests/fixtures/golden_evaluation_dataset.jsonl`](file:///z:/enterprise-intelligence-platform/backend/tests/fixtures/golden_evaluation_dataset.jsonl).
- **Architecture:** 20-question benchmark measuring retrieval precision, citation resolution, abstention accuracy, and keyword coverage.
- **Gaps:** Retrieval precision uses a simplified binary proxy (checks if chunk content exists); citation accuracy uses regex counting without claim-level verification; the dataset lacks ground-truth reference answers and ground-truth passages.

#### Candidate Technology: RAGAS (v0.2+)
- **Core Metrics:** Faithfulness (atomic claim decomposition and entailment), Context Precision (signal-to-noise ranking), Context Recall (ground-truth fact coverage), Response Relevancy (semantic query alignment).
- **Dataset Compatibility:** Requires enriching `golden_evaluation_dataset.jsonl` with `ground_truth` (reference answer) and `ground_truth_contexts` (exact excerpt strings).
- **Cost & Latency:** ~60 LLM calls for 20 questions ($\approx \$0.035$ per run using `gpt-4o-mini`).

#### Architectural Verdict
- **Classification: ADOPT LATER (Enrich Dataset First, Minimal Pure Integration Now).**
- **Justification:** We should not import the entire heavy RAGAS framework immediately. Instead, we port the pure-function Faithfulness and Context Precision algorithms into `backend/evaluation/metrics.py` for zero-cost, deterministic CI runs. Once `golden_evaluation_dataset.jsonl` is enriched with reference answers, full RAGAS LLM-as-a-judge evaluation can be scheduled for offline nightly benchmarks.

---

### 2.4 D. PydanticAI — Typed Agent Alternative

#### Current EIP Implementation
- EIP uses **Pydantic v2** extensively throughout the codebase:
  - Tool schemas: [`KnowledgeBaseSearchInput`](file:///z:/enterprise-intelligence-platform/backend/app/agents/tools.py#L31), [`DocumentAnalysisInput`](file:///z:/enterprise-intelligence-platform/backend/app/agents/tools.py#L36), [`StructuredReportGenerationInput`](file:///z:/enterprise-intelligence-platform/backend/app/agents/tools.py#L40).
  - API request/response models: [`backend/app/schemas/`](file:///z:/enterprise-intelligence-platform/backend/app/schemas/).
  - Structured LLM output: [`backend/app/llm/router.py` L168–L217](file:///z:/enterprise-intelligence-platform/backend/app/llm/router.py#L168-L217) (`generate_structured(messages, response_model=...)`).

#### Candidate Technology: PydanticAI
- **Overview:** An agent framework built by the Pydantic team designed for type-safe LLM applications, typed dependency injection, and model-agnostic structured outputs.
- **Evaluation Against EIP Architecture:**
  1. *Typed Tool Definitions:* EIP already has fully typed tool definitions using Pydantic schemas in `TOOL_SCHEMAS`. PydanticAI’s `@agent.tool` decorator merely wraps this in another syntax.
  2. *Dependency Injection:* FastAPI already provides industry-standard dependency injection (`Depends(get_db)`, `Depends(get_current_user)`). Introducing a secondary DI system inside PydanticAI creates architectural confusion.
  3. *Structured Output & Retries:* EIP’s `generate_structured()` already enforces Pydantic validation over router responses with fallback failover.
  4. *Maturity & Stability:* PydanticAI is in active, rapid early development (v0.0.x / v0.1.x) with frequent breaking API changes, whereas EIP requires enterprise stability.

#### Architectural Verdict
- **Classification: REJECT / UNNECESSARY.**
- **Justification:** PydanticAI duplicates capabilities EIP already implements cleanly using Pydantic v2 and FastAPI. Introducing an early-stage framework adds maintenance risk and dependency bloat without providing unique architectural capabilities.

---

### 2.5 E. Promptfoo — Security Testing & Red Teaming

#### Current EIP Vulnerability Profile
- Engineering documents (incident runbooks, postmortems, architecture RFCs) uploaded by users may contain **indirect prompt injection** strings designed to manipulate agent tool execution or leak system configurations.
- EIP currently has basic regex filtering ([`_strip_instruction_patterns()`](file:///z:/enterprise-intelligence-platform/backend/app/agents/orchestrator.py#L193-L217)), but lacks automated penetration and red-teaming tests in CI.

#### Candidate Technology: Promptfoo
- **Capabilities:** Local, fast CLI tool for prompt evaluation, automated prompt injection red teaming, jailbreak testing, and system prompt leakage detection.
- **Execution & Privacy:** Runs completely locally via Node/CLI (`npx promptfoo eval`). Zero external data sharing; prompts and documents remain within the local build runner.
- **CI Integration:** Native GitHub Actions integration with exit codes and markdown test reports.

#### Architectural Verdict
- **Classification: ADOPT NOW (Phase 1).**
- **Justification:** Promptfoo directly addresses enterprise security requirements by providing automated CI regression testing against document poisoning and prompt injection, complementing our existing unit and integration test suites.

---

### 2.6 F. Provider Reliability & Token Tracking (LiteLLM vs. Custom Providers)

#### Current EIP Implementation
- **Files:** [`backend/app/llm/base.py`](file:///z:/enterprise-intelligence-platform/backend/app/llm/base.py), [`router.py`](file:///z:/enterprise-intelligence-platform/backend/app/llm/router.py), [`openai_client.py`](file:///z:/enterprise-intelligence-platform/backend/app/llm/openai_client.py), [`anthropic_client.py`](file:///z:/enterprise-intelligence-platform/backend/app/llm/anthropic_client.py), [`fake_client.py`](file:///z:/enterprise-intelligence-platform/backend/app/llm/fake_client.py).
- **Architecture:** Abstract base client `BaseLLMClient`, per-provider implementations with custom exponential backoff (1s, 2s, 4s), rate-limit classification, timeout handling, circuit-breaker failover from Claude 3.5 Sonnet to GPT-4o, and deterministic offline simulation (`FakeLLMClient`).

#### Candidate Technology: LiteLLM
- **Capabilities:** Universal I/O interface for 100+ LLMs, automatic token/cost tracking, unified error mapping, and load balancing.
- **Tradeoff Analysis:**
  - *Advantages:* Simplifies future expansion to Google Gemini, AWS Bedrock, or Azure OpenAI via a single completion interface.
  - *Disadvantages:* Introduces an opinionated retry/fallback layer that conflicts with EIP’s fine-grained circuit breaker in [`router.py`](file:///z:/enterprise-intelligence-platform/backend/app/llm/router.py). LiteLLM's error mapping can obscure upstream provider headers (e.g., Anthropic `retry-after`). EIP’s custom client is only ~350 LOC, completely understood, and supports offline deterministic mocking without complex monkey-patching.

#### Recommended Provider-Independent Usage Event Schema
To decouple token tracking and cost accounting from specific providers without adopting LiteLLM, we specify a standardized **`LLMUsageEvent`**:

```python
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime, timezone

@dataclass(frozen=True)
class LLMUsageEvent:
    """Standardized provider-independent usage record for telemetry and billing."""
    event_id: str
    workspace_id: str
    user_id: str
    session_id: Optional[str]
    provider: str                      # "anthropic", "openai", "google", "fake"
    model: str                         # "claude-3-5-sonnet-20241022", "gpt-4o"
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cached_prompt_tokens: int          # For prompt caching accounting
    cost_usd: float
    latency_ms: int
    is_fallback: bool
    status: str                        # "success", "error", "rate_limited"
    error_type: Optional[str] = None
    created_at: datetime = datetime.now(timezone.utc)
```

#### Architectural Verdict
- **Classification: KEEP CUSTOM IMPLEMENTATION (Adopt Standard Usage Schema Now; LiteLLM Later if Expanding to 5+ Providers).**
- **Justification:** EIP's custom provider architecture is lean, reliable, and provides superior circuit-breaker control. Adopting LiteLLM today introduces redundant abstractions. We adopt the unified `LLMUsageEvent` schema immediately to standardize telemetry across both providers and Langfuse.

---

### 2.7 G. Async Document Processing & Ingestion Architecture

#### Current EIP Implementation
- **Files:** [`backend/app/services/document_service.py` L18–L111](file:///z:/enterprise-intelligence-platform/backend/app/services/document_service.py#L18-L111), [`backend/app/api/routes/documents.py` L16–L60](file:///z:/enterprise-intelligence-platform/backend/app/api/routes/documents.py#L16-L60).
- **Execution Model:** **100% SYNCHRONOUS IN REQUEST THREAD.**
  1. The user uploads a file via `POST /workspaces/{id}/documents/upload`.
  2. The route awaits `file.read()`, then directly calls `document_service.upload_and_process(..., db=db)`.
  3. The request thread blocks while executing file hashing, document parsing, block chunking, batch embedding generation (calling OpenAI or Fake client), and PostgreSQL database commits.
  4. Only after all chunks are committed does the endpoint return HTTP 201.
- **Worker Infrastructure:** **None.** No background tasks, Celery workers, or message consumers exist in the running application.
- **Redis Status:** `redis 7.4.0` is installed in the Python virtual environment, but is **NOT integrated** into the application code (no `REDIS_URL` in [`backend/app/core/config.py`](file:///z:/enterprise-intelligence-platform/backend/app/core/config.py)).
- **Deduplication:** Hash-based deduplication (`SHA256`) works for completed documents, but if an in-flight document processing fails or times out, the document is permanently stuck in `status = "processing"`.
- **Server Restart Resilience:** If the server restarts during ingestion, in-flight jobs are abandoned in `status = "processing"`; there is no recovery or retry mechanism.

#### Evaluation of Solutions for EIP

| Solution | Mechanism | Complexity | Enterprise Fit for EIP |
|---|---|---|---|
| **FastAPI `BackgroundTasks`** | In-process asynchronous task execution using Python asyncio. | Very Low (0 new services). | Good interim fix, but jobs do NOT survive server restarts or scaling to multiple pods. |
| **Redis + ARQ / Celery** | Out-of-process distributed worker pool backed by Redis queue. | Moderate (requires Redis container & worker process). | **Recommended Standard:** High throughput, job retries, dead-letter queues, survives web server restarts. |
| **DBOS / Temporal** | Durable execution platform storing complete step state in PostgreSQL. | High (steep learning curve, custom runtime). | **Overkill:** Document parsing and embedding is a simple linear pipeline, not a long-running multi-day business saga. |

#### Architectural Verdict
- **Classification: ADOPT LATER (Phase 2: Redis + ARQ Worker Pool).**
- **Justification:** For development and test benchmarks with synthetic docs (<50 pages), synchronous ingestion completes in <1.5 seconds. For production multi-megabyte PDF processing, synchronous processing risks HTTP gateway 504 timeouts. In Phase 2, integrate a dedicated Redis-backed task queue (`ARQ` or `Celery`), returning HTTP 202 Accepted immediately with a polling status endpoint.

---

## 3. Cross-Technology Comparison Matrix

The table below provides a unified comparison across all evaluated technologies, summarizing existing capabilities, candidate technologies, architectural gaps, and explicit recommendations.

| Capability Area | Existing EIP Implementation | Candidate Technology | Architectural Gap in EIP | Strategic Recommendation |
|---|---|---|---|---|
| **Agent Orchestration** | Custom procedural ReAct loop ([`orchestrator.py`](file:///z:/enterprise-intelligence-platform/backend/app/agents/orchestrator.py)) with thread timeouts and regex parsing. | **LangGraph** (v0.2+) | Lacks token streaming, state checkpointing across crashes, and human-in-the-loop review. | **RUN A PROOF OF CONCEPT / ADOPT LATER (Phase 2)** |
| **LLM Tracing & Observability** | Basic relational table ([`llm_logs`](file:///z:/enterprise-intelligence-platform/backend/app/models/llm_log.py)) logging tokens and cost via static dict. | **Langfuse** (v2.x SDK) | No nested span waterfalls (retrieval $\rightarrow$ rerank $\rightarrow$ LLM), no prompt cache accounting, no eval score links. | **ADOPT NOW (Phase 1: Self-Hosted)** |
| **RAG Quality Evaluation** | 20-question benchmark ([`metrics.py`](file:///z:/enterprise-intelligence-platform/backend/evaluation/metrics.py)) with keyword coverage and content existence proxy. | **RAGAS** (v0.2+) | No claim-level faithfulness, no context recall against reference answers, coarse precision metric. | **ADOPT LATER (Enrich Dataset; Adopt Pure Metrics in Phase 1)** |
| **Typed Agent Framework** | Pydantic v2 schemas for all tools and router structured outputs. | **PydanticAI** | No functional gap; duplicates existing Pydantic validation and FastAPI DI. | **REJECT / UNNECESSARY** |
| **Security Red Teaming** | Regex command stripping ([`orchestrator.py` L193](file:///z:/enterprise-intelligence-platform/backend/app/agents/orchestrator.py#L193)) on untrusted tool outputs. | **Promptfoo** | No automated testing against indirect prompt injection in uploaded PDFs or system prompt leaks in CI. | **ADOPT NOW (Phase 1: CI Pipeline)** |
| **Provider Management** | Custom client trio (Anthropic, OpenAI, Fake) with exponential backoff and circuit breaker failover. | **LiteLLM** | Duplicates working circuit breaker; adds dependency weight without current need. | **KEEP CUSTOM IMPLEMENTATION (Adopt Standard Usage Schema)** |
| **Document Ingestion** | Synchronous execution inside FastAPI request thread; no background workers. | **Redis + Celery / ARQ** | Large files risk HTTP timeout; in-flight jobs lost on server restart; no retry queue. | **ADOPT LATER (Phase 2: Redis Worker)** |

---

## 4. Technical Justifications & Risk Assessments

### 4.1 Langfuse Integration Details
- **Affected Files:**
  - [`backend/app/llm/router.py`](file:///z:/enterprise-intelligence-platform/backend/app/llm/router.py): Add `@observe(as_type="generation")`
  - [`backend/app/retrieval/hybrid.py`](file:///z:/enterprise-intelligence-platform/backend/app/retrieval/hybrid.py): Add `@observe(name="hybrid_retrieval")`
  - [`backend/app/services/rag_service.py`](file:///z:/enterprise-intelligence-platform/backend/app/services/rag_service.py): Add `@observe(name="rag_response_generation")`
  - [`backend/app/agents/orchestrator.py`](file:///z:/enterprise-intelligence-platform/backend/app/agents/orchestrator.py): Add `@observe(name="agent_investigation")`
- **Dependencies:** `langfuse>=2.50.0`
- **Migration Complexity:** Low (decorator-based, non-breaking).
- **Infrastructure & Cost:** Self-hosted Docker container (ClickHouse + Web UI); zero software licensing cost.
- **Security & Privacy:** High compliance; all telemetry stays on-premise/VPC.

### 4.2 Promptfoo Integration Details
- **Affected Files:**
  - `.github/workflows/ci.yml`: Add `promptfoo eval` step.
  - `backend/tests/security/promptfooconfig.yaml`: Test suite definitions.
  - `backend/tests/security/promptfoo_provider.py`: Lightweight test runner adapter.
- **Dependencies:** `promptfoo` CLI (installed via npm in CI runner).
- **Migration Complexity:** Very Low (runs external to Python backend).
- **Risks & Limitations:** Tests consume minor LLM API tokens during CI runs (mitigated by using fake client or lightweight models).

---

## 5. Required Deliverables Summary

This Technology Adoption Audit is accompanied by three detailed architecture and design specifications:
1. **[`docs/research/LANGGRAPH_VS_CUSTOM_AGENT_COMPARISON.md`](file:///z:/enterprise-intelligence-platform/docs/research/LANGGRAPH_VS_CUSTOM_AGENT_COMPARISON.md):** 10-dimension comparison, architectural Q&A, and full working proof-of-concept utilizing EIP's 3 tools.
2. **[`docs/research/AI_OBSERVABILITY_AND_EVALUATION_DESIGN.md`](file:///z:/enterprise-intelligence-platform/docs/research/AI_OBSERVABILITY_AND_EVALUATION_DESIGN.md):** Langfuse distributed tracing architecture, RAGAS metric formulations, dataset enrichment schema, and Promptfoo security configuration.
3. **[`docs/architecture/PROPOSED_AI_ENGINEERING_STACK.md`](file:///z:/enterprise-intelligence-platform/docs/architecture/PROPOSED_AI_ENGINEERING_STACK.md):** Complete target architecture blueprint, provider usage schema, async ingestion design, and phased implementation roadmap.

---

## 6. Final Recommendations: Direct Answers to Core Questions

### 1. Should EIP retain its custom agent, adopt LangGraph, or use a hybrid architecture?
**Recommendation: HYBRID ARCHITECTURE (Keep Custom Now, Introduce LangGraph in Phase 2).**  
Retain the custom agent for the immediate release to satisfy core assessment requirements with zero framework risk. In Phase 2, introduce LangGraph specifically for complex incident investigation graphs requiring streaming and human-in-the-loop review.

### 2. Should Langfuse be adopted, and how should it be integrated?
**Recommendation: ADOPT LANGFUSE NOW (Self-Hosted).**  
Deploy self-hosted Langfuse via Docker Compose to maintain data sovereignty. Instrument the pipeline using the modern v2 `@observe()` decorator at four entry points: `rag_service.py`, `retrieval/hybrid.py`, `llm/router.py`, and `agents/orchestrator.py`. Retain PostgreSQL `llm_logs` as the authoritative relational system-of-record.

### 3. Which RAGAS metrics should be added to our existing evaluation?
**Recommendation: ADOPT FAITHFULNESS & CONTEXT PRECISION IMMEDIATELY (Pure Function); DEFER CONTEXT RECALL UNTIL DATASET ENRICHED.**  
Immediately integrate claim-level Faithfulness and Context Precision into `backend/evaluation/metrics.py`. Enrich `golden_evaluation_dataset.jsonl` with reference answers and context excerpts before enabling full LLM-as-a-judge Context Recall.

### 4. Is PydanticAI worth adopting or does our current Pydantic architecture suffice?
**Recommendation: REJECT / CURRENT ARCHITECTURE SUFFICES.**  
EIP's existing Pydantic v2 schemas and FastAPI dependency injection already provide complete type safety and validation. PydanticAI adds unnecessary abstraction over an already well-structured codebase.

### 5. Should Promptfoo become part of our security-testing workflow?
**Recommendation: ADOPT PROMPTFOO NOW FOR CI SECURITY.**  
Integrate Promptfoo into the GitHub Actions CI pipeline to continuously test against indirect prompt injection in uploaded engineering documents and prevent system prompt leakage.

### 6. Should we retain custom provider management or use LiteLLM?
**Recommendation: KEEP CUSTOM PROVIDER MANAGEMENT; ADOPT STANDARDIZED `LLMUsageEvent`.**  
Retain our custom provider client trio and circuit-breaker router. Adopt the provider-agnostic `LLMUsageEvent` schema to standardize token accounting, caching, and cost telemetry without introducing LiteLLM's redundant retry layers.

### 7. What should be implemented immediately versus deferred?
- **Implement Immediately (Phase 1):**
  1. Promptfoo automated security red-teaming in CI.
  2. Dataset enrichment (`ground_truth`, `ground_truth_context`) and pure-function Faithfulness metrics.
  3. Standardized `LLMUsageEvent` schema in `router.py`.
  4. Langfuse self-hosted instrumentation on RAG and LLM calls.
- **Defer to Phase 2 (Post-Submission):**
  1. LangGraph streaming and human-in-the-loop investigation workflows.
  2. Redis-backed async document ingestion workers (ARQ/Celery).
  3. Full RAGAS LLM-as-a-judge nightly benchmark suite.


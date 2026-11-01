# ADR-DB-005: Auditability and Granular Tracing of Retrieval and Agent Executions

## Status
ACCEPTED

## Context
A primary differentiator of the Engineering Intelligence Platform from consumer chatbots is **evidence traceability and forensic auditability**.

When an engineer conducts an incident investigation or an AI agent executes multi-step research, unexpected outputs or failures require diagnosis:
- *Why was a specific chunk chosen over another?*
- *Did dense search or sparse keyword search surface the evidence?*
- *What was the exact cross-encoder reranking score?*
- *What parameters did the agent send to Tool 2, and what did Tool 2 return?*

We must decide whether intermediate retrieval steps and agent tool traces should be logged only to ephemeral application logs or persisted in relational database tables.

## Decision
We persist structured execution traces in dedicated relational tables:

1. **`retrieval_executions` & `retrieval_candidates`:**
   - Records the raw user query, de-contextualized rewritten query, applied metadata filters, and execution latency.
   - Records the top 20 fused candidates, their individual dense vector cosine scores, BM25 keyword ranks, Reciprocal Rank Fusion (RRF) scores, cross-encoder reranker scores, and a boolean flag (`is_selected_for_context`) indicating whether the chunk was passed to the LLM.
2. **`agent_runs` & `agent_tool_executions`:**
   - Records the user's high-level goal, status (`RUNNING`, `COMPLETED`, `FAILED`, `MAX_STEPS_REACHED`), total step count, and execution duration.
   - Records each sequential tool execution step (1 through 5), tool name (`knowledge_base_search`, `document_analysis`, `structured_report_generation`), validated Pydantic input arguments (JSONB), returned tool output (JSONB), execution latency, and error messages if a tool failed.
3. **Data Retention & Pruning:**
   - Candidate ranking traces (`retrieval_candidates`) are retained for **30 days** to support debugging and evaluation analysis, after which older candidate rows are pruned via an automated background maintenance task.
   - High-level execution summaries (`retrieval_executions`, `agent_runs`, `message_citations`) are retained permanently alongside conversation history.

## Alternatives Considered
- **Ephemeral Logging Only (Stdout / CloudWatch / Datadog):**
  - *Pros:* Zero database storage overhead.
  - *Cons:* Impossible for the frontend UI to render interactive agent step cards or show citation confidence scores dynamically. Hard to run automated SQL-based evaluation queries comparing retrieval algorithms.
- **Permanent Indefinite Storage of All Candidates:**
  - *Pros:* Complete historical record.
  - *Cons:* Storage bloat over time as millions of non-selected candidate rows accumulate.

## Rationale
Persisting retrieval candidate scores and agent tool steps directly in PostgreSQL delivers immediate benefits:
1. Enables the React frontend to display live step-by-step agent progress indicators and tool parameter inspector cards.
2. Fulfills assessment requirements for agent observability and explainability during the live 60-minute evaluation.
3. Provides an empirical ground-truth dataset for computing Context Precision and Context Recall during evaluation runs.

## Consequences
- **Positive:**
  - Complete visibility into agent reasoning and retrieval scoring.
  - Rich debugging telemetry accessible via REST APIs.
- **Negative:**
  - Additional database write per query turn (mitigated by asynchronous batching or lightweight insert operations).


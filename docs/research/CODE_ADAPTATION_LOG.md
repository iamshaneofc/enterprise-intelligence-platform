# Code Adaptation and Reference Repository Integration Log

## 1. Executive Summary
During the Phase 1 backend implementation sprint, our architecture team audited three enterprise open-source reference repositories to extract production battle-tested design patterns. This document provides an audit trail of the architectural mechanisms adapted into our codebase, documenting the source repository, rationale, and target implementation files.

---

## 2. Adaptation Matrix

| Reference Repository | Architectural Pattern Adapted | Implementation in Our Codebase | Technical Benefit |
| :--- | :--- | :--- | :--- |
| **enterprise-knowledge-assistant** | **Short Citation Aliasing (`[c_0]`, `[c_1]`)** | `backend/app/rag/prompt_templates.py`, `backend/app/rag/citations.py` | Eliminates LLM hallucination and string truncation caused by passing long UUIDs into generation prompts. |
| **enterprise-knowledge-assistant** | **Denormalized `workspace_id` on Chunks** | `backend/app/models/document.py`, `backend/app/repositories/vector_repo.py` | Enables direct workspace-scoped vector indexing and similarity search (`ORDER BY embedding <=> :q`) without costly table joins. |
| **enterprise-knowledge-assistant** | **Golden Evaluation Benchmark Format** | `backend/tests/fixtures/golden_evaluation_dataset.jsonl` | Standardized JSONL structure with explicit negative test cases (`expected_to_abstain: true`). |
| **RAG-Enterprise** | **Deterministic Anti-Hallucination Guard (`find_ungrounded_claims`)** | `backend/app/rag/grounding.py` | Regex verification scanning answer outputs for numbers, metrics, dates, and URLs, ensuring every factual claim exists in source chunks. |
| **RAG-Enterprise** | **Abstention Directive Regex (`is_model_abstention`)** | `backend/app/rag/grounding.py` | Accurately identifies `ABSTAIN: insufficient_evidence` and variations to prevent raw model directives from leaking to end users. |
| **RAG-Enterprise** | **XML Context Isolation (`<untrusted_document_context>`)** | `backend/app/rag/prompt_templates.py` | Protects LLM against prompt injection attacks embedded inside parsed third-party documents. |
| **agent-doc-intelligence** | **Graceful Agent Tool Error Envelope** | `backend/app/agents/tools.py` | Envelopes all tool execution returns in `{"ok": bool, "data": ..., "error": ...}` so autonomous agent reasoning loops can self-correct on failures. |
| **agent-doc-intelligence** | **Sliding Window Memory & Coreference Resolution** | `backend/app/memory/manager.py` | Manages token budget with sliding turn window and reformulates conversational pronouns into standalone queries. |

---

## 3. Deep Dive on Adapted Patterns

### A. Short Citation Aliasing (`CitationMap`)
- **Origin:** `reference_repos/enterprise-knowledge-assistant`
- **Problem Solved:** When passing retrieved chunks into an LLM, referencing full document titles or UUIDs in the prompt increases prompt tokens and causes models to truncate IDs or hallucinate citations.
- **Implementation:**
  Our `CitationMap` assigns short markers (`[c_0]`, `[c_1]`, etc.) to retrieved chunks. The LLM is instructed to cite only the short marker. Upon receiving the LLM output, `citation_map.resolve(answer)` scans for markers and translates them back to database entities with document IDs, document titles, snippets, and similarity scores.

### B. Deterministic Anti-Hallucination Guard
- **Origin:** `reference_repos/RAG-Enterprise`
- **Problem Solved:** LLMs frequently hallucinate precise metrics, timestamps, and numbers (e.g., claiming 500 connections instead of 200, or fabricating dates).
- **Implementation:**
  `find_ungrounded_claims(answer, context_chunks)` extracts all dates, metrics with units (e.g., `200 connections`, `4200ms`, `5s`), and URLs from the answer. It verifies their existence against the retrieved chunks. Any discrepancy is returned as an ungrounded claim warning in `ChatResponse.ungrounded_claims`.

### C. Graceful Tool Error Recovery
- **Origin:** `reference_repos/agent-doc-intelligence`
- **Problem Solved:** Standard tool invocations that throw uncaught exceptions crash the entire agent reasoning loop.
- **Implementation:**
  The `AgentToolRegistry.execute_tool` method intercepts all exceptions and invalid inputs, returning `{"ok": False, "error": "..."}`. The observation is fed directly into the agent's scratchpad, allowing the model to analyze the error and try a different tool or corrected query.


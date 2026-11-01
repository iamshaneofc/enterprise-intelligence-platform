# Technical Research & Reference Audits (`docs/research/`)

## 1. Overview
This directory contains the technical reference audits, comparative analyses, technology evaluations, and architectural recommendations produced during the pre-implementation research phase of the **Engineering Intelligence Platform**.

To ensure that our architecture adopts battle-tested enterprise engineering practices while avoiding common anti-patterns, three open-source reference implementations were cloned into `reference_repos/` and audited at the source-code level:
1. **`agent-doc-intelligence` (LeonxLJX):** Agent state machine, in-memory BM25 + RRF, and self-contained LLM-as-a-judge evaluation.
2. **`RAG-Enterprise` (sohrab-phd):** Enterprise knowledge management, deterministic anti-hallucination guards, and database mixins.
3. **`enterprise-knowledge-assistant` (daniella-mv):** Production FastAPI + `pgvector` RAG, short citation aliasing (`[c_0]`), and 20-question golden evaluation suite.

---

## 2. Directory Contents & Artifact Guide

- **[`REFERENCE_REPOSITORY_AUDIT.md`](REFERENCE_REPOSITORY_AUDIT.md):**
  - Exhaustive technical audit of all three codebases covering backend structure, document ingestion, retrieval, agent state, evaluation, security, and observability.
  - Includes a 21-category cross-repository comparison matrix and detailed source-file references.

- **[`TECH_STACK_COMPARISON.md`](TECH_STACK_COMPARISON.md):**
  - Systematic, evidence-based technology evaluation comparing framework selections (FastAPI, React, PostgreSQL/pgvector, PyMuPDF, Claude vs. GPT-4o, custom tool-calling vs. LangGraph).
  - Outlines architectural trade-offs for each technology choice.

- **[`ARCHITECTURE_GAP_ANALYSIS.md`](ARCHITECTURE_GAP_ANALYSIS.md):**
  - Detailed gap analysis comparing our proposed system architecture against the reference implementations.
  - Identifies four critical design refinements to adopt (Short Citation Aliasing, Deterministic Grounding Guards, Robust Abstention Regex, Self-Contained Evaluators).

- **[`ADOPTION_RECOMMENDATIONS.md`](ADOPTION_RECOMMENDATIONS.md):**
  - Actionable recommendations organized into **Category A (ADOPT)**, **Category B (CONSIDER)**, and **Category C (AVOID)**, complete with source file paths, rationales, and impact assessments.

- **[`REPOSITORY_INVENTORY.md`](REPOSITORY_INVENTORY.md):**
  - Exact provenance records, Git commit hashes, branches, commit dates, licensing details, and top-level directory layouts for all three cloned reference repositories.

---

## 3. How This Research Informs Implementation
The insights from this research directly refine our upcoming implementation phases:
1. **Phase 1 (Database & Auth):** Adopting chunk-level `workspace_id` denormalization for faster vector search.
2. **Phase 2 (Ingestion):** Confirming PyMuPDF for high-speed PDF extraction and asynchronous Redis job queuing.
3. **Phase 3 (RAG & Citations):** Implementing `CitationMap` short aliasing (`[c_0]`, `[c_1]`) and deterministic number/URL grounding guards.
4. **Phase 4 (Agent):** Confirming the custom tool-calling loop over LangGraph to maximize code ownership and live evaluation agility.
5. **Phase 5 (Evaluation):** Structuring the 20-question golden dataset with explicit abstention ground truth and automated CLI reporting.


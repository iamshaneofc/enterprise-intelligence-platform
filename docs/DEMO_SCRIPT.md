# Engineering Intelligence Platform — 5–10 Minute Demonstration Script

**Document Type:** Live Demonstration & Video Walkthrough Runbook  
**Target Audience:** Technical Evaluators, Hiring Committee & Engineering Leadership  
**Total Target Duration:** 8 minutes (5–10 minute operational window)  
**Demonstration Mode:** Live Web Application running locally at `http://127.0.0.1:3000` (backed by FastAPI at `http://127.0.0.1:8000`) or deployed cloud URL.

---

## Demonstration Overview & Scene Breakdown

```
+----------------------------------------------------------------------------------------------------+
|                                    DEMO WALKTHROUGH SCHEDULE                                       |
+-------+---------------+-----------------------------------------------+----------------------------+
| Scene | Time Window   | Feature / Workflow Demonstrated               | Primary Capability Proved  |
+-------+---------------+-----------------------------------------------+----------------------------+
| 01    | 0:00 – 0:45   | Architecture Overview & Intro                 | System Mission & Stack     |
| 02    | 0:45 – 1:30   | User Login & Workspace Isolation              | JWT Auth & Multi-Tenancy   |
| 03    | 1:30 – 2:30   | Document Upload & Ingestion Lifecycle         | Parsers & SHA-256 Dedupe   |
| 04    | 2:30 – 3:15   | Chunk Explorer & Embedding Inspection         | Semantic Chunking          |
| 05    | 3:15 – 4:15   | Evidence-Grounded RAG & Inline Citations      | Hybrid Search (pgvector)   |
| 06    | 4:15 – 5:00   | Click-to-Verify Citation Side Drawer          | Source Traceability        |
| 07    | 5:00 – 5:45   | Insufficient Evidence & Honest Abstention     | Evidence Gate & Guardrails |
| 08    | 5:45 – 6:45   | Autonomous Agent Multi-Step Investigation     | 3 Tools & Loop Execution   |
| 09    | 6:45 – 7:30   | Structured Report Generation & Timeline Audit | Inter-Tool Data Chaining   |
| 10    | 7:30 – 8:15   | Live Evaluation Benchmark Dashboard           | 46-Question Quality Run    |
| 11    | 8:15 – 8:45   | LLM Usage Tracking & Observability            | Telemetry & Langfuse       |
+-------+---------------+-----------------------------------------------+----------------------------+
```

---

## Detailed Step-by-Step Demonstration Runbook

### Scene 1: Introduction & Architecture Overview (0:00 – 0:45)
- **Target Screen:** Project Homepage or Terminal / Swagger UI (`/docs`).
- **Presenter Action:** Introduce the project mission.
- **Talking Points:**
  > *"Welcome. Today I am demonstrating the Engineering Intelligence Platform (EIP). Engineering organizations lose hours correlating fragmented incident postmortems, architecture specs, and runbooks. Standard chatbots hallucinate plausible root causes and lack source citations. EIP is built from the ground up for zero-trust evidence retrieval, strict citation grounding, multi-provider LLM fallback, and autonomous multi-tool investigation."*

---

### Scene 2: User Login & Workspace Isolation (0:45 – 1:30)
- **Target Screen:** `http://127.0.0.1:3000/login`
- **Presenter Action:**
  1. Open the login page.
  2. Log in using test credentials (or register a new user).
  3. Land on the main **Overview Dashboard**.
- **Expected Outcome:**
  - JWT token received and securely stored in session state.
  - User profile badge displays role (`engineer` or `admin`).
  - Active workspace (`Production Reliability`) loaded in header dropdown.
- **Talking Points:**
  > *"We begin by logging in. The platform enforces strict multi-tenant workspace isolation. Every document, chunk, vector embedding, and conversation thread is scoped by a workspace ID, preventing cross-tenant data leakage."*

---

### Scene 3: Document Upload & Ingestion Lifecycle (1:30 – 2:30)
- **Target Screen:** `http://127.0.0.1:3000/documents`
- **Presenter Action:**
  1. Click **Documents** in the navigation sidebar.
  2. Drag and drop `backend/tests/fixtures/synthetic_docs/incident_104_postmortem.md` into the upload zone.
  3. Click **Upload Document**.
- **Expected Outcome:**
  - File status displays `PENDING`, transitioning to `PROCESSING`, and then `INDEXED` with a green checkmark badge.
  - Document metadata table displays filename, file size, format (`md`), chunk count (e.g. 5 chunks), and timestamp.
  - Re-uploading the same file displays an immediate duplicate alert powered by SHA-256 hash deduplication.
- **Talking Points:**
  > *"In the Document Manager, we support PDFs, Markdown, CSVs, and plain text. When a file is uploaded, the backend validates its format, computes a SHA-256 hash to prevent redundant re-indexing, parses the content, and divides it into semantic chunks with overlapping boundaries."*

---

### Scene 4: Chunk Explorer & Embedding Inspection (2:30 – 3:15)
- **Target Screen:** Documents page table -> Actions column.
- **Presenter Action:**
  1. Click the **View Chunks** button next to the indexed document.
  2. Scroll through the extracted chunks in the Chunk Explorer modal.
- **Expected Outcome:**
  - Modal opens showing chunk indices (0, 1, 2...), character counts, and verbatim extracted text.
  - Confirms high-dimensional vector embeddings are stored in PostgreSQL (`pgvector`) for each chunk.
- **Talking Points:**
  > *"Clicking 'View Chunks' opens our Chunk Explorer. Reviewers can inspect the exact segmentations that feed our vector engine. Notice how section boundaries are preserved to maintain context continuity during retrieval."*

---

### Scene 5: Evidence-Grounded RAG & Inline Citations (3:15 – 4:15)
- **Target Screen:** `http://127.0.0.1:3000/chat`
- **Presenter Action:**
  1. Click **Knowledge Chat** in the navigation sidebar.
  2. Enter the prompt:
     ```
     What was the start time and documented root cause of Incident 104?
     ```
  3. Click **Send** or press Enter.
- **Expected Outcome:**
  - The system executes hybrid retrieval (dense pgvector cosine search + sparse BM25 lexical match merged via Reciprocal Rank Fusion).
  - The model responds with factual precision:
    > *"Incident 104 started on 2026-03-14 at 14:22 UTC [c_0]. The reported root cause was PostgreSQL connection pool exhaustion triggered by sequential scans on the billing_events table [c_0]."*
  - The response features blue, clickable inline citation pills: `[c_0]`.
- **Talking Points:**
  > *"Notice the response. Unlike standard LLMs that generate unverified claims, every factual statement here is directly anchored to retrieved evidence, indicated by inline citation markers [c_0]. Our hybrid retrieval combines vector semantics with BM25 keyword matching to ensure exact technical terms like 'billing_events' are never missed."*

---

### Scene 6: Click-to-Verify Citation Side Drawer (4:15 – 5:00)
- **Target Screen:** Chat interface.
- **Presenter Action:** Click the `[c_0]` citation pill in the assistant's message.
- **Expected Outcome:**
  - An evidence inspection drawer slides out from the right side of the screen.
  - Displays the source document title (`Incident 104 Postmortem`), chunk index, hybrid similarity score (e.g. `0.884`), and verbatim chunk snippet highlighted.
- **Talking Points:**
  > *"When an engineer or auditor clicks a citation badge, the Evidence Drawer immediately surfaces the verbatim source passage, document name, and confidence score. This provides 100% auditability without navigating away from the investigation."*

---

### Scene 7: Insufficient Evidence & Honest Abstention (5:00 – 5:45)
- **Target Screen:** Chat interface.
- **Presenter Action:**
  1. Enter an out-of-domain or unanswerable query:
     ```
     Explain quantum teleportation entanglement protocols and photon spin states.
     ```
  2. Click **Send**.
- **Expected Outcome:**
  - The `EvidenceSufficiencyGate` analyzes the query and retrieved candidates, detecting that keyword coverage is $< 25\%$.
  - The system short-circuits execution without calling external LLMs (consuming 0 tokens).
  - An amber **Insufficient Evidence Alert** is rendered:
    > *"I do not have sufficient evidence in the uploaded documents to answer this question reliably."*
- **Talking Points:**
  > *"Honest uncertainty is critical in engineering. When asked an out-of-domain question about quantum teleportation, our Evidence Sufficiency Gate detects $< 25\%$ term coverage. Instead of hallucinating a plausible answer, the system immediately abstains, saving token costs and preventing misleading engineering guidance."*

---

### Scene 8: Autonomous Agent Multi-Step Investigation (5:45 – 6:45)
- **Target Screen:** `http://127.0.0.1:3000/agent`
- **Presenter Action:**
  1. Navigate to **Agent Studio**.
  2. In the task prompt input, enter:
     ```
     Investigate recurring database connection exhaustion across all incident reports and compile an executive report.
     ```
  3. Click **Start Investigation**.
- **Expected Outcome:**
  - The agent loop initiates, displaying a multi-step execution plan:
    - Step 1: Knowledge Base Search
    - Step 2: Document Analysis
    - Step 3: Structured Report Generation
  - Step timeline dynamically renders tool inputs, tool execution durations, and intermediate outputs.
- **Talking Points:**
  > *"Now we move to our Autonomous AI Agent. Rather than simple question answering, the agent solves complex engineering tasks by formulating a plan and calling tools. Watch the execution timeline: Step 1 searches the knowledge base for incident documents; Step 2 analyzes the retrieved postmortems to extract failure causes; and Step 3 chains those findings into a structured report."*

---

### Scene 9: Structured Executive Report Generation (6:45 – 7:30)
- **Target Screen:** Agent Studio -> Final Report Tab.
- **Presenter Action:** Scroll through the generated final report in the right-hand panel.
- **Expected Outcome:**
  - A structured markdown report is rendered containing:
    - Executive Summary
    - Incident Chronology & Affected Services
    - Root Cause Analysis (distinguishing reported causes from hypotheses)
    - Actionable Engineering Mitigations (e.g. composite index creation, connection pool limits)
  - The step summary displays `Total Steps: 3`, execution time, and tool status badges (`success`).
- **Talking Points:**
  > *"Here is the final report. Notice how the agent synthesizes findings into an executive briefing with documented facts, timelines, and mitigations. Our custom agent architecture operates with strict parameter validation and a 5-step cap to prevent infinite loops."*

---

### Scene 10: Live Evaluation Benchmark Dashboard (7:30 – 8:15)
- **Target Screen:** `http://127.0.0.1:3000/evaluation`
- **Presenter Action:**
  1. Click **Evaluation** in the sidebar.
  2. Click **Run Evaluation Benchmark** (or view the pre-loaded live run).
- **Expected Outcome:**
  - The backend executes the 46-question golden evaluation suite (`golden_evaluation_dataset.jsonl`).
  - Real quantitative metrics render on the dashboard:
    - Retrieval Precision@5: **0.8043**
    - Context Recall: **0.9348**
    - Mean Reciprocal Rank (MRR): **1.0000**
    - Citation Resolution Rate: **1.0000**
    - Grounding Rate: **0.9674**
    - Abstention Accuracy: **0.8913**
  - Category breakdown charts display performance across Numerical, Factual, Out-of-Domain, and Multi-Document questions.
- **Talking Points:**
  > *"In compliance with Module G, we do not rely on subjective impressions. Our evaluation suite benchmarks 46 curated engineering questions. The system achieves 0.9674 grounding and 1.0000 citation resolution, with honest distinguishing between deterministic context overlap and LLM judge evaluations."*

---

### Scene 11: LLM Usage Tracking & Observability (8:15 – 8:45)
- **Target Screen:** `http://127.0.0.1:3000/settings` or Terminal / DB Query.
- **Presenter Action:**
  1. Navigate to **Settings** to inspect usage telemetry.
  2. Briefly show the `llm_logs` single-entry accounting and Langfuse trace integration.
- **Expected Outcome:**
  - Total tokens, estimated cost in USD, and latency distributions are visible.
  - Proves provider failover resilience (Claude 3.5 Sonnet to GPT-4o).
- **Talking Points:**
  > *"Finally, every LLM interaction is recorded in our PostgreSQL llm_logs table with token counts, latency, and costs, with single-entry accounting preventing double-billing on retries. Langfuse v5 tracing is integrated with fail-safe local fallback. Thank you, and I look forward to your questions."*

---

## Contingency & Offline Fallback Instructions

If running the demo without an active internet connection or external LLM API keys:
1. Ensure `USE_FAKE_LLM=true` and `USE_FAKE_EMBEDDINGS=true` are set in `.env`.
2. The platform will run fully deterministically using the built-in `FakeLLMClient` and regex chunk parser, executing all RAG answers, citation extractions, agent tool chains, and evaluation runs without requiring external network access.


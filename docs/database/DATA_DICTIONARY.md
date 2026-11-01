# Data Dictionary
## Engineering Intelligence Platform
**Document Type:** Technical Data Dictionary  
**Version:** 1.0  
**Phase:** Step 3 — Database Schema Design  
**Status:** Approved for Implementation  

---

## 1. Overview
This Data Dictionary defines every proposed table and column in the **Engineering Intelligence Platform** PostgreSQL 16 + `pgvector` database schema. It catalogs data types, constraints, default values, nullability, and business descriptions across all ten domains.

---

## 2. Table Catalog

```
+----+-----------------------------+-----------------------------------+-----------------------------------------+
| #  | Table Name                  | Domain                            | Primary Responsibility                  |
+----+-----------------------------+-----------------------------------+-----------------------------------------+
| 1  | `workspaces`                | Identity & Access Management      | Tenant boundary for teams/organizations |
| 2  | `users`                     | Identity & Access Management      | Authenticated engineers and admins      |
| 3  | `documents`                 | Document Management & Versioning  | Logical technical document assets       |
| 4  | `document_versions`         | Document Management & Versioning  | Immutable physical file snapshots       |
| 5  | `processing_jobs`           | Document Ingestion & Pipeline     | Asynchronous ingestion task states      |
| 6  | `document_chunks`           | Knowledge & Vector Engine         | Segmented text passages & full-text tsv |
| 7  | `chunk_embeddings`          | Knowledge & Vector Engine         | 1536-dimensional HNSW vector embeddings |
| 8  | `retrieval_executions`      | Retrieval & Grounding Audit       | Search queries, filters, and latencies  |
| 9  | `retrieval_candidates`      | Retrieval & Grounding Audit       | Scored candidate chunks (RRF / rerank)  |
| 10 | `conversations`             | Conversational AI & Citations     | Multi-turn chat sessions & summaries    |
| 11 | `messages`                  | Conversational AI & Citations     | User, assistant, and system turns       |
| 12 | `message_citations`         | Conversational AI & Citations     | Verifiable links to supporting passages |
| 13 | `agent_runs`                | Autonomous Agent Execution        | Multi-step investigative goal loops     |
| 14 | `agent_tool_executions`     | Autonomous Agent Execution        | Granular tool inputs, outputs, errors   |
| 15 | `llm_usage_logs`            | LLM Telemetry & Fallback          | Token counts, costs, and failover logs  |
| 16 | `evaluation_datasets`       | Evaluation & Benchmarking         | Versioned benchmark test suites         |
| 17 | `evaluation_questions`      | Evaluation & Benchmarking         | 20+ curated benchmark question items    |
| 18 | `evaluation_runs`           | Evaluation & Benchmarking         | Automated benchmark execution runs      |
| 19 | `evaluation_results`        | Evaluation & Benchmarking         | Per-question scores and pass/fail audit |
| 20 | `audit_logs`                | System Observability & Activity   | Security and administrative event logs  |
+----+-----------------------------+-----------------------------------+-----------------------------------------+
```

---

## 3. Detailed Table & Column Specifications

### Table 1: `workspaces`
**Domain:** Identity & Access Management  
**Description:** Defines tenant boundaries. All users, documents, and sessions belong to a workspace.

| Column Name | Data Type | Nullable | Default | Key | Description |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `id` | UUID | NO | `gen_random_uuid()` | **PK** | Unique workspace identifier. |
| `name` | VARCHAR(100) | NO | - | - | Display name of the engineering team or company. |
| `slug` | VARCHAR(100) | NO | - | **UK** | URL-friendly unique slug for routing. |
| `created_at` | TIMESTAMPTZ | NO | `NOW()` | - | Timestamp when workspace was registered. |

---

### Table 2: `users`
**Domain:** Identity & Access Management  
**Description:** Represents user accounts for engineers, SREs, and platform administrators.

| Column Name | Data Type | Nullable | Default | Key | Description |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `id` | UUID | NO | `gen_random_uuid()` | **PK** | Unique user identifier. |
| `workspace_id` | UUID | NO | - | **FK** | Reference to `workspaces(id)`. |
| `email` | VARCHAR(255) | NO | - | **UK** | Unique corporate email address. |
| `hashed_password` | VARCHAR(255) | NO | - | - | Bcrypt hashed password string. |
| `full_name` | VARCHAR(150) | NO | - | - | User's full name. |
| `role` | VARCHAR(50) | NO | `'engineer'` | - | Access role: `'admin'`, `'engineer'`, or `'viewer'`. |
| `is_active` | BOOLEAN | NO | `TRUE` | - | Active account status flag. |
| `created_at` | TIMESTAMPTZ | NO | `NOW()` | - | Account creation timestamp. |
| `updated_at` | TIMESTAMPTZ | NO | `NOW()` | - | Profile last update timestamp. |

---

### Table 3: `documents`
**Domain:** Document Management & Versioning  
**Description:** Represents a logical technical document asset across its lifecycle.

| Column Name | Data Type | Nullable | Default | Key | Description |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `id` | UUID | NO | `gen_random_uuid()` | **PK** | Unique logical document identifier. |
| `workspace_id` | UUID | NO | - | **FK** | Reference to owning `workspaces(id)`. |
| `uploaded_by` | UUID | NO | - | **FK** | Reference to uploader `users(id)`. |
| `title` | VARCHAR(255) | NO | - | - | Human-readable document title. |
| `filename` | VARCHAR(255) | NO | - | - | Original uploaded filename. |
| `file_type` | VARCHAR(20) | NO | - | - | File format: `'pdf'`, `'txt'`, `'md'`, or `'csv'`. |
| `is_private` | BOOLEAN | NO | `FALSE` | - | Hybrid privacy flag (true = uploader only). |
| `owner_id` | UUID | NO | - | **FK** | User owning access rights (`users(id)`). |
| `current_version_id`| UUID | YES | NULL | **FK** | Reference to active `document_versions(id)`. |
| `content_hash` | VARCHAR(64) | NO | - | - | SHA-256 hash of active file bytes. |
| `status` | VARCHAR(50) | NO | `'PENDING'` | - | State: `'PENDING'`, `'PROCESSING'`, `'INDEXED'`, `'FAILED'`. |
| `metadata` | JSONB | NO | `'{}'::jsonb`| - | Metadata tags (`project`, `subsystem`, `environment`). |
| `is_deleted` | BOOLEAN | NO | `FALSE` | - | Soft-delete flag. |
| `created_at` | TIMESTAMPTZ | NO | `NOW()` | - | Upload timestamp. |
| `updated_at` | TIMESTAMPTZ | NO | `NOW()` | - | Last modification timestamp. |

---

### Table 4: `document_versions`
**Domain:** Document Management & Versioning  
**Description:** Immutable snapshot of a specific uploaded file version.

| Column Name | Data Type | Nullable | Default | Key | Description |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `id` | UUID | NO | `gen_random_uuid()` | **PK** | Unique document version identifier. |
| `document_id` | UUID | NO | - | **FK** | Reference to parent `documents(id)`. |
| `version_number` | INTEGER | NO | 1 | - | Monotonically increasing version index (1, 2, ...). |
| `file_size_bytes` | INTEGER | NO | - | - | Exact file size in bytes (max 25MB). |
| `storage_path` | VARCHAR(500) | NO | - | - | S3 object key or encrypted storage path. |
| `content_hash` | VARCHAR(64) | NO | - | - | SHA-256 hash of this version's raw bytes. |
| `extraction_summary`| TEXT | YES | NULL | - | Optional summary of extracted text. |
| `metadata` | JSONB | NO | `'{}'::jsonb`| - | Structural metadata (page count, layout details). |
| `created_by` | UUID | NO | - | **FK** | Reference to user who uploaded this version. |
| `created_at` | TIMESTAMPTZ | NO | `NOW()` | - | Timestamp when this version was created. |

---

### Table 5: `processing_jobs`
**Domain:** Document Ingestion & Pipeline  
**Description:** Tracks the asynchronous processing lifecycle of a document version.

| Column Name | Data Type | Nullable | Default | Key | Description |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `id` | UUID | NO | `gen_random_uuid()` | **PK** | Unique processing job identifier. |
| `document_id` | UUID | NO | - | **FK** | Reference to parent `documents(id)`. |
| `document_version_id`| UUID | NO | - | **FK** | Reference to target `document_versions(id)`. |
| `status` | VARCHAR(50) | NO | `'PENDING'` | - | State: `'PENDING'`, `'PROCESSING'`, `'COMPLETED'`, `'FAILED'`. |
| `stage` | VARCHAR(50) | NO | `'EXTRACTION'` | - | Stage: `'EXTRACTION'`, `'CHUNKING'`, `'EMBEDDING'`, `'INDEXING'`. |
| `attempts` | INTEGER | NO | 0 | - | Number of execution retries attempted. |
| `max_attempts` | INTEGER | NO | 3 | - | Maximum allowed attempts before marking FAILED. |
| `error_message` | TEXT | YES | NULL | - | Human-readable error summary. |
| `error_traceback` | TEXT | YES | NULL | - | Full Python stack trace on failure. |
| `lock_token` | VARCHAR(100) | YES | NULL | - | Distributed Redis lock token preventing duplicates. |
| `started_at` | TIMESTAMPTZ | YES | NULL | - | Timestamp when worker began processing. |
| `completed_at` | TIMESTAMPTZ | YES | NULL | - | Timestamp when processing concluded. |
| `created_at` | TIMESTAMPTZ | NO | `NOW()` | - | Timestamp when job was enqueued. |

---

### Table 6: `document_chunks`
**Domain:** Knowledge & Vector Engine  
**Description:** Stores segmented text passages and full-text search representations.

| Column Name | Data Type | Nullable | Default | Key | Description |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `id` | UUID | NO | `gen_random_uuid()` | **PK** | Unique chunk identifier. |
| `document_version_id`| UUID | NO | - | **FK** | Reference to source `document_versions(id)`. |
| `document_id` | UUID | NO | - | **FK** | Reference to parent `documents(id)`. |
| `workspace_id` | UUID | NO | - | **FK** | Reference to owning `workspaces(id)`. |
| `chunk_index` | INTEGER | NO | - | - | Sequential index of chunk in document (0, 1, 2...). |
| `content` | TEXT | NO | - | - | Raw text content of the chunk (~512 tokens). |
| `token_count` | INTEGER | NO | - | - | Exact token count (cl100k_base). |
| `page_number` | INTEGER | YES | NULL | - | Source page number for citations. |
| `section_heading` | VARCHAR(255) | YES | NULL | - | Preceding Markdown/PDF section heading. |
| `metadata` | JSONB | NO | `'{}'::jsonb`| - | Heading hierarchy and character offsets. |
| `tsv_content` | TSVECTOR | NO | *Generated* | - | Generated column: `to_tsvector('english', content)`. |
| `created_at` | TIMESTAMPTZ | NO | `NOW()` | - | Chunk creation timestamp. |

---

### Table 7: `chunk_embeddings`
**Domain:** Knowledge & Vector Engine  
**Description:** Stores dense vector representations indexed via HNSW in `pgvector`.

| Column Name | Data Type | Nullable | Default | Key | Description |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `id` | UUID | NO | `gen_random_uuid()` | **PK** | Unique embedding identifier. |
| `chunk_id` | UUID | NO | - | **FK, UK** | 1-to-1 reference to `document_chunks(id)`. |
| `embedding_model` | VARCHAR(100) | NO | - | - | Model used: `'text-embedding-3-small'`. |
| `dimensions` | INTEGER | NO | 1536 | - | Vector dimensionality (1536). |
| `embedding` | vector(1536) | NO | - | - | 1536-dimensional floating-point vector. |
| `created_at` | TIMESTAMPTZ | NO | `NOW()` | - | Embedding generation timestamp. |

---

### Table 8: `retrieval_executions`
**Domain:** Retrieval & Grounding Audit  
**Description:** Audits search operations executed by RAG or AI Agents.

| Column Name | Data Type | Nullable | Default | Key | Description |
| :--- | :--- | :---: | :---: | :--- |
| `id` | UUID | NO | `gen_random_uuid()` | **PK** | Unique retrieval execution identifier. |
| `conversation_id` | UUID | YES | NULL | **FK** | Reference to active `conversations(id)`. |
| `message_id` | UUID | YES | NULL | - | Reference to user `messages(id)` if applicable. |
| `raw_query` | TEXT | NO | - | - | Original prompt input by user. |
| `rewritten_query` | TEXT | YES | NULL | - | De-contextualized query after memory resolution. |
| `filters_applied` | JSONB | NO | `'{}'::jsonb`| - | Metadata filters applied (`project`, `env`). |
| `dense_candidates_count`| INTEGER | NO | 0 | - | Chunks retrieved by pgvector. |
| `sparse_candidates_count`| INTEGER | NO | 0 | - | Chunks retrieved by BM25 full-text. |
| `fused_candidates_count`| INTEGER | NO | 0 | - | Chunks after Reciprocal Rank Fusion (RRF). |
| `reranked_candidates_count`| INTEGER | NO | 0 | - | Top candidates evaluated by neural reranker. |
| `reranker_model` | VARCHAR(100) | YES | NULL | - | Reranker model identifier used. |
| `execution_duration_ms`| INTEGER | NO | - | - | Total search latency in milliseconds. |
| `created_at` | TIMESTAMPTZ | NO | `NOW()` | - | Execution timestamp. |

---

### Table 9: `retrieval_candidates`
**Domain:** Retrieval & Grounding Audit  
**Description:** Granular candidate scoring breakdown for transparency and evaluation.

| Column Name | Data Type | Nullable | Default | Key | Description |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `id` | UUID | NO | `gen_random_uuid()` | **PK** | Unique candidate record identifier. |
| `retrieval_execution_id`| UUID | NO | - | **FK** | Reference to parent `retrieval_executions(id)`. |
| `chunk_id` | UUID | NO | - | **FK** | Reference to evaluated `document_chunks(id)`. |
| `dense_rank` | INTEGER | YES | NULL | - | Rank in dense vector search. |
| `dense_score` | NUMERIC(7, 5)| YES | NULL | - | Cosine similarity score. |
| `sparse_rank` | INTEGER | YES | NULL | - | Rank in BM25 lexical search. |
| `sparse_score` | NUMERIC(10, 5)| YES | NULL | - | BM25 full-text score. |
| `rrf_score` | NUMERIC(7, 5)| YES | NULL | - | Fused Reciprocal Rank Fusion score. |
| `rerank_score` | NUMERIC(7, 5)| YES | NULL | - | Cross-encoder calibrated score. |
| `is_selected_for_context`| BOOLEAN | NO | `FALSE` | - | Flag indicating inclusion in LLM prompt. |

---

### Table 10: `conversations`
**Domain:** Conversational AI & Citations  
**Description:** Manages multi-turn technical investigation chat sessions.

| Column Name | Data Type | Nullable | Default | Key | Description |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `id` | UUID | NO | `gen_random_uuid()` | **PK** | Unique conversation session identifier. |
| `workspace_id` | UUID | NO | - | **FK** | Reference to owning `workspaces(id)`. |
| `user_id` | UUID | NO | - | **FK** | Reference to creator `users(id)`. |
| `title` | VARCHAR(255) | NO | `'New Investigation'` | - | User or auto-generated session title. |
| `context_summary` | TEXT | YES | NULL | - | Semantic summary of turns older than 4 turns. |
| `is_archived` | BOOLEAN | NO | `FALSE` | - | Archive flag. |
| `created_at` | TIMESTAMPTZ | NO | `NOW()` | - | Session creation timestamp. |
| `updated_at` | TIMESTAMPTZ | NO | `NOW()` | - | Timestamp of last user/assistant message. |

---

### Table 11: `messages`
**Domain:** Conversational AI & Citations  
**Description:** Individual conversational turns in a session.

| Column Name | Data Type | Nullable | Default | Key | Description |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `id` | UUID | NO | `gen_random_uuid()` | **PK** | Unique message identifier. |
| `conversation_id` | UUID | NO | - | **FK** | Reference to parent `conversations(id)`. |
| `sender_type` | VARCHAR(20) | NO | - | - | Role: `'USER'`, `'ASSISTANT'`, or `'SYSTEM'`. |
| `content` | TEXT | NO | - | - | Full markdown message text body. |
| `model_used` | VARCHAR(100) | YES | NULL | - | Model that generated response (if assistant). |
| `retrieval_execution_id`| UUID | YES | NULL | **FK** | Reference to `retrieval_executions(id)`. |
| `created_at` | TIMESTAMPTZ | NO | `NOW()` | - | Message creation timestamp. |

---

### Table 12: `message_citations`
**Domain:** Conversational AI & Citations  
**Description:** Direct grounding links mapping claims in an answer to source passages.

| Column Name | Data Type | Nullable | Default | Key | Description |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `id` | UUID | NO | `gen_random_uuid()` | **PK** | Unique citation identifier. |
| `message_id` | UUID | NO | - | **FK** | Reference to parent `messages(id)`. |
| `chunk_id` | UUID | YES | NULL | **FK** | Reference to source `document_chunks(id)`. |
| `document_version_id`| UUID | NO | - | **FK** | Reference to `document_versions(id)`. |
| `relevance_score` | NUMERIC(7, 5)| NO | - | - | Calibrated relevance score (0.00000 - 1.00000). |
| `citation_marker` | VARCHAR(50) | NO | - | - | Inline marker (e.g., `'[Doc: 104, Chunk: 3]'`). |
| `cited_text_snippet` | TEXT | NO | - | - | Verbatim excerpt supporting the assertion. |
| `created_at` | TIMESTAMPTZ | NO | `NOW()` | - | Citation creation timestamp. |

---

### Table 13: `agent_runs`
**Domain:** Autonomous Agent Execution  
**Description:** Tracks autonomous multi-step investigative goal loops.

| Column Name | Data Type | Nullable | Default | Key | Description |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `id` | UUID | NO | `gen_random_uuid()` | **PK** | Unique agent run identifier. |
| `conversation_id` | UUID | YES | NULL | **FK** | Reference to `conversations(id)`. |
| `user_id` | UUID | NO | - | **FK** | Reference to initiator `users(id)`. |
| `goal` | TEXT | NO | - | - | High-level user investigation objective. |
| `status` | VARCHAR(50) | NO | `'RUNNING'` | - | State: `'RUNNING'`, `'COMPLETED'`, `'FAILED'`, `'MAX_STEPS_REACHED'`. |
| `total_steps` | INTEGER | NO | 0 | - | Number of tool steps executed. |
| `max_steps` | INTEGER | NO | 5 | - | Step cap enforcing loop termination (max 5). |
| `duration_ms` | INTEGER | YES | NULL | - | Total runtime latency in milliseconds. |
| `final_response` | TEXT | YES | NULL | - | Synthesized final response or executive report. |
| `error_message` | TEXT | YES | NULL | - | Error summary if execution failed. |
| `created_at` | TIMESTAMPTZ | NO | `NOW()` | - | Run start timestamp. |
| `completed_at` | TIMESTAMPTZ | YES | NULL | - | Run completion timestamp. |

---

### Table 14: `agent_tool_executions`
**Domain:** Autonomous Agent Execution  
**Description:** Detailed audit of each individual tool invocation within an agent run.

| Column Name | Data Type | Nullable | Default | Key | Description |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `id` | UUID | NO | `gen_random_uuid()` | **PK** | Unique tool execution identifier. |
| `agent_run_id` | UUID | NO | - | **FK** | Reference to parent `agent_runs(id)`. |
| `step_number` | INTEGER | NO | - | - | Sequential step counter (1 to 5). |
| `tool_name` | VARCHAR(100) | NO | - | - | Tool: `'knowledge_base_search'`, `'document_analysis'`, `'structured_report_generation'`. |
| `input_arguments` | JSONB | NO | - | - | Pydantic-validated tool arguments. |
| `output_result` | JSONB | YES | NULL | - | Structured tool result payload. |
| `status` | VARCHAR(50) | NO | - | - | Status: `'SUCCESS'`, `'ERROR'`, or `'TIMEOUT'`. |
| `duration_ms` | INTEGER | NO | - | - | Latency of the tool call in milliseconds. |
| `error_message` | TEXT | YES | NULL | - | Error stack or timeout message on failure. |
| `created_at` | TIMESTAMPTZ | NO | `NOW()` | - | Tool invocation timestamp. |

---

### Table 15: `llm_usage_logs`
**Domain:** LLM Telemetry & Fallback  
**Description:** Fine-grained token usage, financial cost, and fallback telemetry.

| Column Name | Data Type | Nullable | Default | Key | Description |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `id` | UUID | NO | `gen_random_uuid()` | **PK** | Unique log identifier. |
| `workspace_id` | UUID | NO | - | **FK** | Reference to owning `workspaces(id)`. |
| `user_id` | UUID | NO | - | **FK** | Reference to initiating `users(id)`. |
| `conversation_id` | UUID | YES | NULL | **FK** | Reference to `conversations(id)` if applicable. |
| `provider` | VARCHAR(50) | NO | - | - | Provider used: `'anthropic'` or `'openai'`. |
| `model` | VARCHAR(100) | NO | - | - | Model: `'claude-3-5-sonnet'`, `'gpt-4o'`, etc. |
| `call_type` | VARCHAR(50) | NO | - | - | Purpose: `'rag_synthesis'`, `'agent_reasoning'`, `'embedding'`. |
| `prompt_tokens` | INTEGER | NO | - | - | Input token count. |
| `completion_tokens`| INTEGER | NO | - | - | Output token count. |
| `total_tokens` | INTEGER | NO | - | - | Total tokens consumed. |
| `estimated_cost_usd`| NUMERIC(10, 6)| NO | - | - | Calculated cost in USD. |
| `latency_ms` | INTEGER | NO | - | - | API roundtrip latency in milliseconds. |
| `fallback_occurred`| BOOLEAN | NO | `FALSE` | - | Flag indicating fallback circuit breaker triggered. |
| `fallback_reason` | TEXT | YES | NULL | - | Exception description (e.g., HTTP 429 rate limit). |
| `created_at` | TIMESTAMPTZ | NO | `NOW()` | - | API call timestamp. |

---

### Table 16: `evaluation_datasets`
**Domain:** Evaluation & Benchmarking  
**Description:** Stores versioned benchmark test suites.

| Column Name | Data Type | Nullable | Default | Key | Description |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `id` | UUID | NO | `gen_random_uuid()` | **PK** | Unique dataset identifier. |
| `name` | VARCHAR(150) | NO | - | - | Suite name (e.g., `'Engineering Benchmark Core'`). |
| `description` | TEXT | YES | NULL | - | Description of tested topics and failure modes. |
| `version` | VARCHAR(50) | NO | `'1.0.0'` | - | Version tag. |
| `is_active` | BOOLEAN | NO | `TRUE` | - | Active suite flag. |
| `created_at` | TIMESTAMPTZ | NO | `NOW()` | - | Creation timestamp. |

---

### Table 17: `evaluation_questions`
**Domain:** Evaluation & Benchmarking  
**Description:** Curated test questions (minimum 20 questions required by assessment).

| Column Name | Data Type | Nullable | Default | Key | Description |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `id` | UUID | NO | `gen_random_uuid()` | **PK** | Unique question identifier. |
| `dataset_id` | UUID | NO | - | **FK** | Reference to parent `evaluation_datasets(id)`. |
| `question_text` | TEXT | NO | - | - | Benchmark prompt string. |
| `expected_answer` | TEXT | NO | - | - | Ground truth reference answer. |
| `reference_document_ids`| JSONB | NO | `'[]'::jsonb`| - | Array of document IDs containing truth. |
| `category` | VARCHAR(50) | NO | - | - | Category: `'FACTUAL'`, `'SYNTHESIS'`, `'CONTRADICTION'`, `'NEGATIVE'`. |
| `created_at` | TIMESTAMPTZ | NO | `NOW()` | - | Question creation timestamp. |

---

### Table 18: `evaluation_runs`
**Domain:** Evaluation & Benchmarking  
**Description:** Records automated benchmark runs and aggregated RAGAS quality scores.

| Column Name | Data Type | Nullable | Default | Key | Description |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `id` | UUID | NO | `gen_random_uuid()` | **PK** | Unique evaluation run identifier. |
| `dataset_id` | UUID | NO | - | **FK** | Reference to evaluated `evaluation_datasets(id)`. |
| `run_name` | VARCHAR(150) | NO | - | - | Run label (e.g., `'Claude 3.5 Sonnet Hybrid RRF'`). |
| `llm_provider` | VARCHAR(50) | NO | - | - | Tested LLM provider. |
| `llm_model` | VARCHAR(100) | NO | - | - | Tested LLM model name. |
| `retrieval_strategy`| VARCHAR(100) | NO | - | - | Retrieval pipeline configuration. |
| `status` | VARCHAR(50) | NO | `'RUNNING'` | - | State: `'RUNNING'`, `'COMPLETED'`, or `'FAILED'`. |
| `total_questions` | INTEGER | NO | 0 | - | Number of questions evaluated (minimum 20). |
| `faithfulness_score`| NUMERIC(5, 4)| YES | NULL | - | Average RAGAS Faithfulness score (0.0000 - 1.0000). |
| `context_precision` | NUMERIC(5, 4)| YES | NULL | - | Average Context Precision score. |
| `context_recall` | NUMERIC(5, 4)| YES | NULL | - | Average Context Recall score. |
| `answer_relevance` | NUMERIC(5, 4)| YES | NULL | - | Average Answer Relevance score. |
| `hallucination_rate`| NUMERIC(5, 4)| YES | NULL | - | Rate of unsupported assertions. |
| `negative_rejection_accuracy`| NUMERIC(5, 4)| YES | NULL | - | Refusal accuracy on out-of-domain questions. |
| `avg_latency_ms` | INTEGER | YES | NULL | - | Average query latency across the run. |
| `total_cost_usd` | NUMERIC(10, 4)| YES | NULL | - | Cumulative dollar cost of the benchmark run. |
| `created_at` | TIMESTAMPTZ | NO | `NOW()` | - | Execution start timestamp. |
| `completed_at` | TIMESTAMPTZ | YES | NULL | - | Execution completion timestamp. |

---

### Table 19: `evaluation_results`
**Domain:** Evaluation & Benchmarking  
**Description:** Itemized per-question scores, answers, and pass/fail audits.

| Column Name | Data Type | Nullable | Default | Key | Description |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `id` | UUID | NO | `gen_random_uuid()` | **PK** | Unique result record identifier. |
| `evaluation_run_id` | UUID | NO | - | **FK** | Reference to parent `evaluation_runs(id)`. |
| `question_id` | UUID | NO | - | **FK** | Reference to `evaluation_questions(id)`. |
| `generated_answer` | TEXT | NO | - | - | AI response generated during evaluation. |
| `retrieved_chunk_ids`| JSONB | NO | `'[]'::jsonb`| - | List of chunk IDs retrieved for prompt. |
| `faithfulness` | NUMERIC(5, 4)| YES | NULL | - | Question-level Faithfulness score. |
| `context_precision` | NUMERIC(5, 4)| YES | NULL | - | Question-level Context Precision score. |
| `answer_relevance` | NUMERIC(5, 4)| YES | NULL | - | Question-level Answer Relevance score. |
| `latency_ms` | INTEGER | NO | - | - | Query latency in milliseconds. |
| `pass_fail` | BOOLEAN | NO | - | - | Automated pass/fail determination. |
| `failure_reason` | TEXT | YES | NULL | - | Grounding failure or hallucination explanation. |
| `created_at` | TIMESTAMPTZ | NO | `NOW()` | - | Result recorded timestamp. |

---

### Table 20: `audit_logs`
**Domain:** System Observability & Activity  
**Description:** Immutable security and administrative activity log.

| Column Name | Data Type | Nullable | Default | Key | Description |
| :--- | :--- | :---: | :---: | :--- |
| `id` | UUID | NO | `gen_random_uuid()` | **PK** | Unique audit log identifier. |
| `workspace_id` | UUID | NO | - | **FK** | Reference to `workspaces(id)`. |
| `user_id` | UUID | YES | NULL | **FK** | Reference to actor `users(id)` if authenticated. |
| `action` | VARCHAR(100) | NO | - | - | Action name (e.g., `'DOCUMENT_UPLOAD'`). |
| `resource_type` | VARCHAR(100) | NO | - | - | Resource entity type (e.g., `'document'`). |
| `resource_id` | VARCHAR(100) | NO | - | - | Identifier of affected resource. |
| `details` | JSONB | NO | `'{}'::jsonb`| - | Structured event context payload. |
| `ip_address` | VARCHAR(45) | YES | NULL | - | Client IPv4 or IPv6 address. |
| `created_at` | TIMESTAMPTZ | NO | `NOW()` | - | Audit event timestamp. |


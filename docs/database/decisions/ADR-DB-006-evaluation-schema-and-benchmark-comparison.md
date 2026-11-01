# ADR-DB-006: Normalized Evaluation Schema for Benchmark Comparisons

## Status
ACCEPTED

## Context
Module G (AI Evaluation) mandates establishing an automated evaluation dataset of at least 20 curated questions and measuring retrieval relevance, answer correctness, grounding (faithfulness), hallucination rate, latency, and token consumption.

To make evaluation scientific, repeatable, and verifiable:
1. Multiple prompt templates, LLM models (Claude 3.5 Sonnet vs. GPT-4o), and retrieval strategies (Dense-only vs. Hybrid RRF vs. Cross-Encoder) must be benchmarked against the identical ground-truth dataset.
2. Reviewers must be able to compare historical evaluation runs to see whether a code change improved or degraded retrieval accuracy.
3. Every individual question must record its generated answer, retrieved chunk IDs, individual metric scores, and pass/fail status.

## Decision
We implement a **Normalized 4-Table Evaluation Schema**:

1. **`evaluation_datasets`:**
   - Defines versioned benchmark suites (e.g., `"Engineering Core Benchmark v1.0"`).
   - Allows activating/deactivating benchmark suites without losing historical test runs.
2. **`evaluation_questions` (Minimum 20 Questions):**
   - Stores the curated question prompt, expected ground-truth answer, and reference document IDs.
   - Categorized across four explicit archetypes:
     - `FACTUAL`: Single-document factual extraction.
     - `SYNTHESIS`: Multi-document analytical synthesis.
     - `CONTRADICTION`: Conflicting document detection.
     - `NEGATIVE`: Out-of-domain unanswerable guardrail test.
3. **`evaluation_runs`:**
   - Represents an automated execution of a benchmark suite.
   - Stores the tested configuration: `llm_provider`, `llm_model`, `retrieval_strategy`, and aggregated metrics (average faithfulness, context precision, context recall, answer relevance, hallucination rate, negative rejection accuracy, average latency, and total dollar cost).
4. **`evaluation_results`:**
   - Detailed item-level breakdown storing the generated answer, retrieved chunks, individual RAGAS metric scores, pass/fail status, and failure explanation for each question.

## Alternatives Considered
- **File-Based JSON Evaluation Reports Only:**
  - *Pros:* Simple to dump to disk.
  - *Cons:* Difficult to query, filter, or visualize in the frontend dashboard. Does not support automated regression alerts or database-driven comparisons between commits.
- **Single Denormalized Evaluation Log Table:**
  - *Pros:* One table.
  - *Cons:* Duplicates question text and configuration across every run, leading to data inconsistencies when question text is refined.

## Rationale
Normalizing datasets, questions, runs, and results into relational tables provides a production-grade benchmarking platform:
- The frontend can render historical trend charts (e.g., Faithfulness over time).
- Automated CI/CD test scripts can query `SELECT * FROM evaluation_runs ORDER BY created_at DESC LIMIT 2` to verify that a code change did not cause regression.
- Reviewers can inspect granular question-level evidence directly via REST APIs.

## Consequences
- **Positive:**
  - Repeatable, observable, and comparable evaluation runs.
  - Direct relational support for the 20+ question benchmark requirement.
  - Clean separation between test fixtures and test execution results.
- **Negative:**
  - Requires maintaining the 4 tables and writing test results via transactions.


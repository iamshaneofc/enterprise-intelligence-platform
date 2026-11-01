# Evaluation Dataset & Deterministic Context Metrics Report
**Engineering Intelligence Platform (EIP)**  
**Date:** November 2026  
**Status:** Completed & Empirically Validated (Offline Mock Provider Mode)  

---

## 1. Executive Summary & Review Scope

This report documents the expansion and formalization of the Engineering Intelligence Platform (EIP) evaluation benchmark. The benchmark has been expanded from a 20-question baseline to a 46-question golden evaluation dataset spanning seven operational categories.

### Important Methodological Clarifications
1. **Deterministic Heuristic Metrics vs. Official RAGAS LLM-Judges:** The context metrics implemented in `backend/evaluation/metrics.py` (`compute_context_precision`, `compute_context_recall`, and `compute_f1_token_overlap`) are **pure-function, deterministic algorithms** based on closed-form set overlap and lexical ranking. They are **NOT** the official RAGAS library metrics (which rely on external LLM judges such as GPT-4 to score answer relevancy and faithfulness).
2. **Provider Environment:** The empirical results documented below were generated using `FakeLLMClient` (`fake-claude-3-5-sonnet`) and `FakeEmbeddingProvider` (`fake-embedding-1536`) in an offline, deterministic test environment.
3. **Live Production Expectations:** While the pre-generation evidence gate and post-generation claim verifier will enforce the same deterministic rules in production, live stochastic models (Claude 3.5 Sonnet, GPT-4o) introduce natural language variance. Live production evaluation with real credentials will yield slightly different absolute scores.

---

## 2. Dataset Expansion & Taxonomy

The golden evaluation dataset (`backend/tests/fixtures/golden_evaluation_dataset.jsonl`) contains 46 human-verified questions with ground-truth target answers, verbatim ground-truth context excerpts, source document associations, and expected citation markers.

### Question Categories Breakdown

| Category | Count | Proportion | Description | Example Target |
|:---|:---:|:---:|:---|:---|
| **Direct Factual** | 12 | 26.1% | Explicit facts, components, endpoints, and architecture primitives | JWKS public key endpoint, composite index on `billing_ledger` |
| **Numerical & Analytical** | 12 | 26.1% | Exact thresholds, connection pool limits, timeouts, latency SLAs | 200 pool connections, 4200ms circuit breaker, 24h JWT TTL |
| **Date & Timeline** | 4 | 8.7% | Incident postmortem timestamps, cron start times, rotation intervals | 2026-03-15 14:22 UTC start, 90-day RSA key rotation |
| **Policy & Procedural** | 5 | 10.9% | Operational procedures, runbook remediation commands, shell syntax | `kubectl rollout restart`, `pg_terminate_backend()` |
| **Multi-Document Synthesis** | 3 | 6.5% | Inquiries requiring synthesizing information across distinct documents | Correlating token storage (Redis + Postgres) across auth & DB docs |
| **Unanswerable / Out-of-Domain**| 9 | 19.6% | Queries completely absent from knowledge base requiring abstention | Quantum teleportation, French bouillabaisse, BGP core routers |
| **Ambiguous / Conflicting** | 1 | 2.2% | Questions with competing numbers or overlapping definitions | Connection acquisition timeout (5s) vs transaction timeout (3s) |
| **Total** | **46** | **100%** | Comprehensive domain coverage | — |

---

## 3. Mathematical Metric Definitions (Pure-Function / Deterministic)

To eliminate cost, network instability, and LLM-judge subjectivity during automated CI/CD runs, all metrics are implemented as deterministic mathematical formulas.

### A. Deterministic Context Precision@K

Context Precision measures whether ground-truth relevant chunks among the retrieved items are ranked higher towards top positions:

$$\text{Context Precision@K} = \frac{\sum_{k=1}^K \left( \text{Precision@}k \times v_k \right)}{\sum_{k=1}^K v_k}$$

where:
- $v_k \in \{0, 1\}$ denotes the binary relevance of the chunk at rank $k$. Relevance is evaluated via lexical token overlap ($ \ge 20\% $ informative content tokens) and number/date match against `ground_truth_context`.
- $\text{Precision@}k = \frac{\sum_{i=1}^k v_i}{k}$ is the precision computed at cutoff $k$.
- If `ground_truth_context` is empty (unanswerable/abstention question), $\text{Context Precision} = 1.0$. If no retrieved chunk is relevant, $\text{Context Precision} = 0.0$.

### B. Deterministic Context Recall

Context Recall measures the proportion of ground-truth statements or sentences attributable to the retrieved context chunks:

$$\text{Context Recall} = \frac{\sum_{s \in S_{\text{gt}}} \mathbb{I}(\text{attributable}(s, C))}{|S_{\text{gt}}|}$$

where:
- $S_{\text{gt}}$ is the set of constituent sentences/clauses in `ground_truth_context`.
- $C = \bigcup_{k=1}^K c_k$ is the concatenated retrieved context text.
- $\mathbb{I}(\text{attributable}(s, C)) = 1$ if the informative tokens of sentence $s$ have $\ge 40\%$ coverage in $C$ and any numerical values present in $s$ match values in $C$.
- If $S_{\text{gt}}$ is empty, $\text{Context Recall} = 1.0$.

### C. Token F1 Overlap (`f1_score`)

Measures token-level precision, recall, and harmonic F1 overlap between the generated answer $P$ and the ground truth $T$:

$$\text{Precision} = \frac{|P \cap T|}{|P|}, \quad \text{Recall} = \frac{|P \cap T|}{|T|}$$

$$\text{F1} = \frac{2 \cdot \text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$

Abstention boundary rules:
- If `expected_to_abstain` is True and the system abstains: $\text{F1} = 1.0$.
- If `expected_to_abstain` is True and the system attempts to answer: $\text{F1} = 0.0$.
- If `expected_to_abstain` is False and the system abstains: $\text{F1} = 0.0$.

---

## 4. Empirical Evaluation Results (Offline Mode)

Executed via `python -m backend.evaluation.runner` using `FakeLLMClient` and `FakeEmbeddingProvider`.

### Aggregate Summary Table

| Metric Group | Metric | Score | Target | Assessment |
|:---|:---|:---:|:---:|:---|
| **Retrieval** | Precision@5 | **0.8043** | $\ge 0.70$ | Exceeded |
| | Recall@5 | **0.8043** | $\ge 0.70$ | Exceeded |
| | MRR | **1.0000** | $\ge 0.90$ | Perfect |
| **Citation & Grounding** | Citation Resolution Rate | **1.0000** | $1.0000$ | Perfect |
| | Evidence Grounding Rate | **0.9674** | $\ge 0.90$ | Exceeded |
| | Hallucination Rate (Offline) | **0.0000** | $\le 0.05$ | Zero ungrounded claims |
| **Abstention & Safety** | Abstention Accuracy | **0.8913** | $\ge 0.85$ | Exceeded |
| | False Abstention Rate | **0.0870** | $\le 0.10$ | Within tolerance |
| | False Answer Rate | **0.0217** | $\le 0.05$ | Near zero |
| **Context Quality** | Deterministic Context Precision | **0.7847** | $\ge 0.75$ | Exceeded |
| | Deterministic Context Recall | **0.9348** | $\ge 0.85$ | Exceeded |
| | Token F1 Overlap | **0.4996** | $\ge 0.40$ | Exceeded |
| **Performance** | Average Latency (Simulated) | **41.8 ms** | $< 500$ ms | Ultra-low latency |

---

### Category-Specific Breakdown

| Category | Count | Grounding Rate | Hallucination Rate | Abstention Accuracy | Context Precision | Context Recall | Token F1 |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Date & Timeline** | 4 | 1.0000 | 0.0000 | 1.0000 | 0.7431 | 1.0000 | 0.4228 |
| **Numerical & Analytical** | 12 | 1.0000 | 0.0000 | 0.9167 | 0.6972 | 0.9167 | 0.3784 |
| **Direct Factual** | 12 | 0.9583 | 0.0000 | 0.9167 | 0.6736 | 0.9167 | 0.4541 |
| **Policy & Procedural** | 5 | 0.8000 | 0.0000 | 1.0000 | 0.8067 | 0.8000 | 0.4758 |
| **Unanswerable** | 9 | 1.0000 | 0.0000 | 0.8889 | 1.0000 | 1.0000 | 0.8889 |
| **Multi-Doc Synthesis** | 3 | 1.0000 | 0.0000 | 0.3333 | 1.0000 | 1.0000 | 0.2267 |
| **Ambiguous/Conflict** | 1 | 1.0000 | 0.0000 | 1.0000 | 0.6389 | 1.0000 | 0.2424 |

---

## 5. Live Production Requirements

To execute this benchmark against live models:
1. Set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in environment.
2. Set `USE_FAKE_LLM=false` and `USE_FAKE_EMBEDDINGS=false`.
3. Run `python -m backend.evaluation.runner --fake-llm=False --fake-embeddings=False`.

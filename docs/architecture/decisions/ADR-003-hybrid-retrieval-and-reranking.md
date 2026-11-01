# ADR-003: Hybrid Retrieval with Reciprocal Rank Fusion and Cross-Encoder Reranking

## Status
ACCEPTED

## Context
The technical assessment mandates implementing at least one retrieval improvement in Module B (Advanced RAG Architecture) and Section 4 (Advanced Engineering Challenges). The system must process technical engineering documentation, including system architecture guides, incident postmortems, infrastructure runbooks, and error logs.

Technical documents present a distinct retrieval challenge:
1. They contain critical alphanumeric identifiers (e.g., `CVE-2024-3094`, `HTTP 504`, `OOMKilled`, `ConnectionPoolTimeoutException`, `v1.28.3`) where exact lexical matches are non-negotiable.
2. They contain conceptual descriptions (e.g., "service became unresponsive due to database resource starvation") where semantic vector matching is required.

We must decide on the optimal retrieval pipeline to ensure maximum evidence recall, precision, and hallucination prevention.

## Decision
We implement a two-stage **Hybrid Retrieval Pipeline** with **Reciprocal Rank Fusion (RRF)**, followed by **Cross-Encoder Reranking**:

1. **Stage 1A (Dense Semantic Retrieval):** Query embedding generated via `text-embedding-3-small` (1536d) searched against `document_chunks.embedding` using PostgreSQL `pgvector` HNSW cosine distance (`<=>`).
2. **Stage 1B (Sparse Lexical Retrieval):** Full-text keyword search executed across `document_chunks.content` using PostgreSQL `to_tsvector` / GIN indexing (BM25 equivalent).
3. **Stage 2 (Reciprocal Rank Fusion - RRF):** Merge results from dense and sparse candidate lists using the standard RRF algorithm:
   $$RRF\_Score(d) = \sum_{m \in \{dense, sparse\}} \frac{1}{k + rank_m(d)} \quad (k=60)$$
4. **Stage 3 (Cross-Encoder Reranking):** Pass the top 15-20 fused candidates through a cross-encoder model (or lightweight neural reranker) to evaluate query-document pair relevance directly, outputting the top 5 most grounded chunks for LLM prompt context injection.
5. **Confidence Gate:** Chunks with reranked relevance scores below a minimum threshold ($\tau < 0.65$) are rejected. If zero chunks survive, the RAG orchestrator triggers an honest "insufficient evidence" response rather than passing irrelevant context to the LLM.

## Alternatives Considered
- **Dense Vector Search Only:**
  - *Pros:* Simple to implement.
  - *Cons:* Frequently misses exact version numbers, configuration flags, and error codes where small subword token changes ruin cosine similarity.
- **Sparse Keyword Search Only (BM25 / Elasticsearch):**
  - *Pros:* Excellent exact match for error codes.
  - *Cons:* Completely blind to synonyms, paraphrased technical concepts, and high-level analytical questions.
- **LLM-Based Reranking (Prompting GPT-4o to rank chunks):**
  - *Pros:* High reasoning capability.
  - *Cons:* High token cost and excessive latency (adding 1-2 seconds per query), unsuited for interactive chat.

## Rationale
Combining dense semantic embeddings with PostgreSQL full-text search directly inside PostgreSQL provides the highest retrieval recall without introducing external search engines like Elasticsearch. Cross-encoder reranking then computes cross-attention over the query and chunk simultaneously, resolving embedding cosine distance limitations (where vector embeddings compress text into independent fixed-size vectors).

## Consequences
- **Positive:**
  - Dramatically improves Context Precision and Context Recall for technical engineering terminology.
  - Eliminates false-positive chunks before they reach the LLM, reducing token cost and preventing hallucinations.
  - Meets and exceeds the assessment's retrieval improvement mandate.
- **Negative:**
  - Adds ~40-80ms compute latency for the reranking step.
  - Requires maintaining GIN full-text indexes alongside HNSW vector indexes in PostgreSQL.


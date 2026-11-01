# ADR-002: PostgreSQL with pgvector for Unified Relational and Vector Storage

## Status
ACCEPTED

## Context
The platform requires persistence for two fundamentally different types of data:
1. **Relational & Transactional State:** Users, authentication credentials, document metadata, processing job logs, multi-turn conversation sessions, messages, citations, agent tool execution audits, and evaluation metrics.
2. **High-Dimensional Vector Embeddings:** 1536-dimensional semantic vector embeddings generated for document chunks and user queries.

We must decide whether to use a dedicated standalone vector database (such as Pinecone, Qdrant, Milvus, or Weaviate) paired with a relational database, or use a unified database solution with PostgreSQL and the `pgvector` extension.

## Decision
We select **PostgreSQL 16 with the `pgvector` extension** as our unified relational and vector database engine.

All relational tables (`users`, `documents`, `conversations`, `messages`, `agent_executions`, etc.) and the vector store (`document_chunks.embedding` column with an HNSW cosine index) reside within the same database cluster.

## Alternatives Considered
- **Pinecone / Qdrant + PostgreSQL (Dual-Store Architecture):**
  - *Pros:* Specialized vector indexing optimizations, serverless scaling.
  - *Cons:* Dual-store consistency issues (orphaned vectors when documents are deleted in PostgreSQL, transactional split-brain during partial ingestion failures), latency overhead of querying two disparate cloud databases, external cloud dependencies requiring separate API keys and network hops, and heightened operational complexity.
- **SQLite + ChromaDB (Local-Only Storage):**
  - *Pros:* Zero external setup for local prototyping.
  - *Cons:* Concurrency bottlenecks (table locking on SQLite writes), inadequate for production cloud multi-worker deployment, fails the enterprise-grade expectation of the technical assessment.

## Rationale
Using PostgreSQL with `pgvector` offers decisive advantages:
1. **ACID Transactional Integrity:** Document records, chunk texts, and vector embeddings are committed or rolled back atomically in a single database transaction. If embedding fails, the entire chunking step can roll back cleanly without leaving orphaned vectors.
2. **Atomic Hybrid Filtering:** Queries can join document metadata (e.g., `workspace_id`, `file_type`, `created_at`) with vector similarity (`<=>` cosine operator) in a single SQL statement, eliminating the two-stage "fetch IDs then filter" pattern required by external vector DBs.
3. **Operational Simplicity:** Only one database to provision, back up, migrate, and monitor in both local Docker Compose and production cloud environments (AWS RDS natively supports `pgvector`).
4. **HNSW Index Support:** `pgvector` provides state-of-the-art Hierarchical Navigable Small World (HNSW) indexing, delivering sub-10ms approximate nearest neighbor retrieval at high recall.

## Consequences
- **Positive:**
  - Zero dual-store synchronization bugs.
  - Unified backup, restore, and migration workflows using Alembic.
  - Reduced cloud infrastructure footprint and cost.
- **Negative:**
  - For massive corpora (millions of documents), dedicated vector engines offer more specialized memory tiering; however, for enterprise knowledge bases (<100,000 chunks), PostgreSQL with `pgvector` delivers exceptional performance well within operational tolerances.


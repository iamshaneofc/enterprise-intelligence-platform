# ADR-DB-003: Dedicated Chunk Embeddings Storage and Vector Indexing

## Status
ACCEPTED

## Context
Each extracted text chunk must be represented as a dense high-dimensional vector embedding for semantic similarity search. We must decide how to store these vectors in PostgreSQL using `pgvector`:
1. As an inline `vector(1536)` column directly inside the `document_chunks` table.
2. In a dedicated `chunk_embeddings` table linked via a 1-to-1 foreign key relationship to `document_chunks`.

We must also consider how embedding model changes or dimensionality shifts impact the physical schema.

## Decision
We store vector embeddings in a dedicated **`chunk_embeddings`** table with a 1-to-1 foreign key to `document_chunks`:
- `id`: UUID (PK)
- `chunk_id`: UUID (FK -> document_chunks.id ON DELETE CASCADE, UNIQUE)
- `embedding_model`: VARCHAR(100) (e.g., `'text-embedding-3-small'`)
- `dimensions`: INTEGER (e.g., `1536`)
- `embedding`: vector(1536) NOT NULL
- `created_at`: TIMESTAMPTZ DEFAULT NOW()

Indexing is configured using **HNSW (Hierarchical Navigable Small World)** with cosine distance:
```sql
CREATE INDEX idx_chunk_embeddings_hnsw 
ON chunk_embeddings 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

## Alternatives Considered
- **Inline Vector Column on `document_chunks`:**
  - *Pros:* Single table; eliminates a `JOIN` during retrieval.
  - *Cons:* Bloats table row size. PostgreSQL reads larger pages when querying text or metadata alone (e.g., retrieving chunk text for citation popovers or LLM context assembly), degrading buffer cache efficiency. Furthermore, changing embedding models or re-indexing requires modifying the primary chunk table schema.
- **External Vector DB (Pinecone / Qdrant):**
  - *Pros:* Offloaded compute.
  - *Cons:* Dual-store synchronization bugs, external cloud network latency, separate billing, and failure to support ACID transactions on chunk deletion.

## Rationale
1. **Memory & I/O Efficiency:** Isolating 1536-dimensional floating-point arrays (6 KB per chunk) into `chunk_embeddings` keeps the `document_chunks` table compact and fast for full-text search, citation lookups, and administrative text browsing.
2. **Model Versioning & Migration Agility:** Storing `embedding_model` and `dimensions` allows the system to support multiple embedding models simultaneously or run parallel evaluations comparing embedding quality without modifying the fundamental chunk text schema.
3. **Sub-10ms Approximate Nearest Neighbor (ANN):** HNSW indexing provides superior query throughput and recall compared to IVFFlat, eliminating the need to train index centroids on large datasets before indexing.

## Consequences
- **Positive:**
  - Clean separation between semantic text data and vector math representations.
  - Efficient PostgreSQL buffer pool usage.
  - Sub-10ms similarity search via HNSW.
- **Negative:**
  - Requires a single inner join between `chunk_embeddings` and `document_chunks` during vector retrieval (mitigated by the clustered unique index on `chunk_id`).


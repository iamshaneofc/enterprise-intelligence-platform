# ADR-DB-004: Soft Delete vs. Hard Delete Strategy for Documents and Vectors

## Status
ACCEPTED

## Context
When an engineer deletes a technical document, the platform must balance two competing operational requirements:
1. **User Safety and Auditability:** Accidental deletions should be reversible, and historical conversation messages that cite the deleted document must not crash or display broken citation links.
2. **Vector Index Hygiene & Information Governance:** Chunks from decommissioned or deleted documents must never be returned in search results or RAG prompts, and permanent deletion must leave zero orphaned vectors in `pgvector`.

## Decision
We implement a **Hybrid Two-Tier Deletion Strategy**:

1. **Tier 1: User-Facing Soft Deletion (`is_deleted = TRUE`):**
   - When an engineer clicks "Delete Document" in the UI, the API sets `documents.is_deleted = TRUE` and records `updated_at = NOW()`.
   - The document immediately disappears from document manager views.
   - **Retrieval Filtration:** All hybrid search queries enforce `WHERE documents.is_deleted = FALSE` via an indexed join. Chunks from soft-deleted documents are instantly excluded from vector and full-text searches.
   - **Citation Preservation:** Historical conversations referencing chunks from this document continue to display cited text snippets, as the underlying `document_chunks` records remain intact.
2. **Tier 2: Permanent Purge via Foreign Key Cascades (`ON DELETE CASCADE`):**
   - When an administrator initiates a permanent purge (or an automated retention policy expires after 30 days), the `documents` row is deleted directly.
   - Database foreign keys enforce cascading removal:
     $$\text{documents} \xrightarrow{\text{CASCADE}} \text{document\_versions} \xrightarrow{\text{CASCADE}} \text{document\_chunks} \xrightarrow{\text{CASCADE}} \text{chunk\_embeddings}$$
   - Any raw files in S3/object storage are deleted by a background cleanup worker.
   - `message_citations.chunk_id` is configured with `ON DELETE SET NULL`, preserving the message and citation text snippet while nullifying the direct foreign key pointer to avoid constraint violations.

## Alternatives Considered
- **Immediate Hard Delete Only:**
  - *Pros:* Simpler queries.
  - *Cons:* Destroys historical conversations citing the deleted document and allows no accidental deletion recovery.
- **Pure Soft Delete Only (Never Purge):**
  - *Pros:* Complete audit trail.
  - *Cons:* Causes indefinite vector index bloat and violates enterprise data governance / GDPR right-to-be-forgotten mandates.

## Rationale
This hybrid pattern prevents accidental data loss, maintains conversational auditability for past investigations, guarantees zero orphaned vectors during permanent purges, and ensures deleted documents never leak into future RAG answers.

## Consequences
- **Positive:**
  - Zero orphaned chunks or vector embeddings upon permanent deletion.
  - Historical chat messages retain evidence integrity even if source documents are decommissioned.
  - Immediate exclusion of soft-deleted documents from all semantic and full-text search queries.
- **Negative:**
  - Search queries must include a filter on `documents.is_deleted = FALSE`.


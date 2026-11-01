# ADR-DB-002: Immutable Document Versioning for Citation Integrity

## Status
ACCEPTED

## Context
In engineering intelligence systems, technical documentation changes over time: architecture specifications are updated, runbooks are modified after new outages, and postmortems receive retrospective amendments.

If documents are updated in-place (overwriting existing chunks and vectors):
1. **Broken Citation Grounding:** Past conversation answers citing *"Chunk 4 of Runbook X"* will suddenly point to modified or deleted text, destroying traceability and reproducibility.
2. **Evaluation Inconsistency:** Evaluation benchmark runs comparing model performance over time cannot be verified if the underlying document text shifts underneath the evaluations.
3. **Loss of Audit History:** Engineers cannot compare what a runbook stated *during* an outage versus what was added *after* the postmortem.

## Decision
We separate the logical document asset from its physical content versions by introducing two distinct entities:
1. **`documents` (Logical Entity):** Maintains the stable identity, workspace association, title, current active version pointer (`current_version_id`), and overall lifecycle state.
2. **`document_versions` (Immutable Entity):** Represents an immutable, point-in-time physical file snapshot. Stores `version_number` (1, 2, ...), `content_hash` (SHA-256), `file_size_bytes`, `storage_path`, and creation timestamp.

All downstream semantic assets (`document_chunks`, `chunk_embeddings`, `processing_jobs`, and `message_citations`) reference the immutable `document_version_id`.

## Alternatives Considered
- **In-Place Document Overwrites (Single Table `documents`):**
  - *Pros:* Simple table design.
  - *Cons:* Destroys historical citation integrity. Any document update invalidates all previous conversation citations and makes forensic debugging impossible.
- **Git-like Content-Addressable Storage Blob System:**
  - *Pros:* Maximal deduplication.
  - *Cons:* Vastly overengineered for an enterprise RAG assessment; adds unnecessary tree traversal complexity.

## Rationale
Separating logical document metadata from immutable version snapshots ensures that:
- Every citation (`message_citations`) permanently points to the exact chunk text, page number, and version used when the LLM generated the response.
- Updating a document creates a new `document_version`, triggers chunking/embedding on the new version, and switches `documents.current_version_id` atomically once indexing completes.
- Inactive past versions can be preserved for historical citation lookup or pruned according to retention policies.

## Consequences
- **Positive:**
  - 100% citation traceability and factual auditability.
  - Zero-downtime document re-indexing (active queries use the current version until the new version is fully indexed).
  - Enables document version diffing in future features.
- **Negative:**
  - Requires maintaining foreign keys to `document_versions` rather than directly to `documents`.
  - Additional storage overhead if many versions are created (mitigated by deduplication checks on `content_hash`).


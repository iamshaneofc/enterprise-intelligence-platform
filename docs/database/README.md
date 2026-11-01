# Database Design & Domain Modeling (`docs/database/`)

## 1. Overview
This directory contains the complete Domain-Driven Design (DDD) domain model, physical PostgreSQL + `pgvector` database schema specifications, data dictionary, Entity Relationship Diagrams (ERD), domain maps, and database Architecture Decision Records (ADRs) for the **Engineering Intelligence Platform**.

It establishes a technically sound, normalized, and immutable data architecture before application implementation begins.

---

## 2. Directory Contents & Artifact Guide

### Core Database Specifications
- **[`DOMAIN_MODEL.md`](DOMAIN_MODEL.md):**
  - High-level domain-driven design specification.
  - Details the ten bounded contexts, aggregate roots, entities, value objects, business rules, and state machines.
  - Includes realistic step-by-step domain walkthroughs (Document Ingestion, Evidence-Grounded RAG, Autonomous Agent Investigation) and the requirement-to-entity traceability matrix.

- **[`DATABASE_SCHEMA.md`](DATABASE_SCHEMA.md):**
  - Table-by-table physical schema specification for PostgreSQL 16 and `pgvector`.
  - Details all 20 tables, columns, data types, primary/foreign keys, check constraints, default values, and cascading delete rules.
  - Documents the HNSW vector index (`vector_cosine_ops`), full-text search `tsvector` generated columns, query pattern justifications, and Row-Level Security (RLS) policies.

- **[`DATA_DICTIONARY.md`](DATA_DICTIONARY.md):**
  - Exhaustive reference dictionary documenting every single proposed table and field with nullability, default values, key types, and business descriptions.

---

### Visual Diagrams
- **Entity Relationship Diagram (Physical Schema):**
  - **Rendered Image:** [`ERD.png`](ERD.png) (High-resolution 1.27 MB diagram showing all 20 tables, primary keys, foreign keys, and cardinalities).
  - **Editable Source:** [`ERD.mmd`](ERD.mmd) (Mermaid ER diagram source code).
- **Domain Boundaries & Context Map:**
  - **Rendered Image:** [`DOMAIN_DIAGRAM.png`](DOMAIN_DIAGRAM.png) (Bounded context map showing aggregate relationships across the ten domains).
  - **Editable Source:** [`DOMAIN_DIAGRAM.mmd`](DOMAIN_DIAGRAM.mmd) (Mermaid flowchart source code).

---

### Database Architecture Decision Records (`decisions/`)
Standalone ADR files documenting the context, decisions, trade-offs, and consequences of critical database design choices:

1. **[`ADR-DB-001: Workspace-Level Multi-Tenancy and Access Model`](decisions/ADR-DB-001-workspace-tenant-isolation-model.md)** — Decision to adopt shared-schema multi-tenancy with `workspace_id` foreign keys and hybrid access schema readiness (pending product confirmation).
2. **[`ADR-DB-002: Immutable Document Versioning for Citation Integrity`](decisions/ADR-DB-002-immutable-document-versioning.md)** — Decision to separate logical `documents` from physical `document_versions` to prevent broken citations when runbooks are updated.
3. **[`ADR-DB-003: Dedicated Chunk Embeddings Storage and Vector Indexing`](decisions/ADR-DB-003-pgvector-chunk-embedding-storage.md)** — Decision to store vectors in a dedicated `chunk_embeddings` table indexed via HNSW cosine distance (`vector_cosine_ops`).
4. **[`ADR-DB-004: Soft Delete vs. Hard Delete Strategy for Documents and Vectors`](decisions/ADR-DB-004-soft-delete-vs-hard-delete-strategy.md)** — Two-tier deletion pattern: user soft delete (`is_deleted = TRUE`) with immediate retrieval exclusion, and admin hard purge via `ON DELETE CASCADE` leaving zero orphaned vectors.
5. **[`ADR-DB-005: Auditability and Granular Tracing of Retrieval and Agent Executions`](decisions/ADR-DB-005-auditability-of-agent-and-retrieval-traces.md)** — Relational persistence of candidate scoring (dense, sparse, RRF, reranker) and agent tool parameters for complete observability.
6. **[`ADR-DB-006: Normalized Evaluation Schema for Benchmark Comparisons`](decisions/ADR-DB-006-evaluation-schema-and-benchmark-comparison.md)** — Normalized 4-table schema (`evaluation_datasets`, `evaluation_questions`, `evaluation_runs`, `evaluation_results`) supporting the 20+ question benchmark requirement.

---

## 3. Maintenance & Diagram Updates
When modifying schema definitions:
1. Update `DATABASE_SCHEMA.md` and `DATA_DICTIONARY.md`.
2. Update the editable `.mmd` diagram files (`ERD.mmd` or `DOMAIN_DIAGRAM.mmd`).
3. Re-render the corresponding `.png` files via the Kroki rendering script.
4. Record any fundamental architectural shifts in a new ADR under `docs/database/decisions/`.


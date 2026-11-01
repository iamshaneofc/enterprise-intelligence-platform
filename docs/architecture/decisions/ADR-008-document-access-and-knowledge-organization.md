# ADR-008: Document Access Model and Knowledge Base Organization

## Status
PROPOSED (Pending User Confirmation of Business Scope)

## Context
Section 15 of the Step 1 Product Requirements Document (PRD) identifies two foundational business decisions that must be resolved prior to finalizing database schemas and access control rules:

1. **Decision A: Document Access Model**
   - *Option 1 (Private Documents):* Each engineer can access and query only their own uploaded documents.
   - *Option 2 (Organization-Wide Documents):* All authorized members of an engineering organization share access to all uploaded documents.
   - *Option 3 (Hybrid Access Model):* Documents can be private to the uploader, restricted to a specific team, or shared organization-wide.

2. **Decision B: Knowledge Base Organization**
   - *Option 1 (One Shared Knowledge Base):* All technical documents belong to a single, unified vector space.
   - *Option 2 (Separate Team / Project Knowledge Bases):* Documents and vector embeddings are physically isolated by project or engineering team.
   - *Option 3 (Hybrid Knowledge Base):* A unified organization knowledge base coexists with dedicated project/team spaces.

We must analyze the trade-offs, recommend a pragmatic default that fulfills the assessment objectives, design a database schema that prevents future breaking migrations, and explicitly document what requires user confirmation.

---

## Analysis of Decision A: Document Access Model

### Trade-Off Analysis
| Model | Architectural Complexity | Assessment Alignment | Real-World Engineering Fit |
| :--- | :--- | :--- | :--- |
| **Private Only** | Low: Simple `WHERE user_id = :uid` filter. | Low: Incompatible with collaborative multi-document incident investigation across engineers. | Poor: Engineering runbooks and postmortems are inherently communal. |
| **Org-Wide Only** | Low: `WHERE workspace_id = :ws_id` filter across all queries. | High: Perfectly enables cross-document incident analysis and SRE postmortem synthesis. | High: Matches internal wiki/runbook behavior (Confluence/Notion). |
| **Hybrid Model** | Medium: Requires Access Control Lists (ACLs) or permission tables checking user, team, and public flags. | High: Future-proof, but adds authorization logic that must be rigorously tested. | Ideal: Matches production enterprise security. |

### Architectural Recommendation for Decision A
We recommend adopting a **Workspace-Shared Default with Hybrid Schema Readiness**:
- **Default Behavior for MVP Implementation:** All documents uploaded within a workspace are accessible to all authenticated engineers within that workspace (`WHERE workspace_id = :current_workspace_id`). This directly facilitates the assessment's primary scenario: *"Analyze our internal technical documentation and identify the most common reasons for system failures."*
- **Schema Pre-Architected for Hybrid Evolution:** The `documents` table includes `is_private: BOOLEAN DEFAULT FALSE` and `owner_id: UUID REFERENCES users(id)`.
- When `is_private = TRUE`, retrieval queries automatically apply `AND (is_private = FALSE OR owner_id = :current_user_id)`.
- This provides immediate collaborative utility for the 24-hour evaluation while supporting private documents without schema migrations.

---

## Analysis of Decision B: Knowledge Base Organization

### Trade-Off Analysis
| Model | Architectural Complexity | Retrieval Quality & Cross-System Insights |
| :--- | :--- | :--- |
| **One Shared KB** | Low: Single `document_chunks` table with `pgvector` HNSW index. | **Highest:** Engineering incidents frequently cross technical boundaries (e.g., an API gateway timeout caused by database pool exhaustion in another service). |
| **Separate Physical KBs** | High: Requires dynamic table creation, multiple vector indexes, or separate database schemas. | **Poor:** Silos information; user must know in advance which team repository holds the answer. |
| **Hybrid (Metadata-Scoped)** | Low-Medium: Single vector index with SQL metadata filtering (`WHERE metadata->>'project' = :proj`). | **Excellent:** Users can execute broad cross-system investigations by default, or optionally scope queries to a specific project. |

### Architectural Recommendation for Decision B
We recommend adopting a **Single Unified Vector Space with Metadata-Scoped Filtering**:
- All document chunks reside in a unified `document_chunks` table indexed by `pgvector`.
- Every chunk inherits metadata tags from its parent document: `project`, `subsystem`, `environment` (e.g., `production`, `staging`), and `document_type` (e.g., `incident_report`, `architecture_spec`, `runbook`).
- Standard queries search the entire knowledge base to uncover cross-system failure patterns.
- If an engineer or agent specifically requests *"Search only Kubernetes runbooks"*, the retrieval engine applies an atomic SQL metadata filter: `WHERE (metadata->>'document_type' = 'runbook')`.

---

## Confirmation Required from Product Owner
To prevent assumptions, the following choices are presented for explicit user confirmation:

> [!IMPORTANT]
> **Action Required from Product Owner:**
> 1. **Confirm Document Access Model:** Proceed with **Workspace-Shared Default with Hybrid Schema Readiness** (Option 3 hybrid schema, Option 2 default behavior)?
> 2. **Confirm Knowledge Base Organization:** Proceed with **Single Unified Vector Space with Metadata Filtering** (Option 3 hybrid metadata filtering)?

Unless modified by the user, the architecture documents and database schemas will implement this hybrid-ready design.


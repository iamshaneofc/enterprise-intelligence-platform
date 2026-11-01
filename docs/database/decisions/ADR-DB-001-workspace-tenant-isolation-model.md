# ADR-DB-001: Workspace-Level Multi-Tenancy and Access Model

## Status
ACCEPTED (with Hybrid Access Readiness pending Product Owner confirmation)

## Context
The Engineering Intelligence Platform is designed to support engineering teams, Site Reliability Engineers, and DevOps personnel collaborating on technical documentation. We must establish how data is partitioned across tenants, users, and teams:
1. Multi-tenant database per client (separate PostgreSQL database per organization).
2. Schema-per-tenant (separate PostgreSQL schemas within a single database).
3. Shared database, shared schema with foreign key isolation (`workspace_id` column on all tenant-owned entities).

Furthermore, we must resolve **Decision A (Document Access Model)** from the PRD: whether documents are strictly private to individual users, shared across an entire organization/workspace, or hybrid.

## Decision
We adopt a **Shared Database, Shared Schema Multi-Tenant Architecture** scoped by a `workspace_id` foreign key across all primary entities (`users`, `documents`, `conversations`, `llm_usage_logs`, `audit_logs`).

For **Document Access (Decision A)**, we implement a **Workspace-Shared Default with Hybrid Schema Readiness**:
- **Default Behavior:** All engineering documents uploaded within a workspace are accessible to all authenticated engineers in that workspace (`WHERE workspace_id = :current_workspace_id`).
- **Hybrid Readiness:** The `documents` table includes `is_private: BOOLEAN DEFAULT FALSE` and `owner_id: UUID REFERENCES users(id)`. When `is_private = TRUE`, the document is accessible only to its owner and workspace administrators.
- **Query Scoping:** Every database repository automatically injects `workspace_id = :current_workspace_id` into `WHERE` clauses.

## Alternatives Considered
- **Database-per-Tenant:**
  - *Pros:* Complete physical isolation.
  - *Cons:* Immense operational overhead, complex connection pooling, challenging cross-tenant migrations, and completely impractical for a 24-hour evaluation and single-developer project.
- **Strictly Private Documents Only:**
  - *Pros:* Simple user-level filtering (`WHERE user_id = :uid`).
  - *Cons:* Directly breaks collaborative engineering incident investigation. SREs and developers need to query shared postmortems, architecture runbooks, and failure histories created by other team members.

## Rationale
In real-world engineering environments, technical incident reports and runbooks are communal assets. A workspace-shared model with an optional `is_private` flag satisfies immediate collaborative requirements while providing an un-opinionated schema that can easily support strict privacy in the future without database migrations. Shared-schema multi-tenancy keeps connection pool management simple and allows PostgreSQL and `pgvector` to maximize memory efficiency.

## Consequences
- **Positive:**
  - Single connection pool, straightforward migrations via Alembic.
  - Instant collaborative querying of shared technical documentation across team members.
  - Zero schema churn when transitioning between private and shared document modes.
- **Negative:**
  - All queries must rigorously include `workspace_id` filters to prevent cross-tenant data leakage.


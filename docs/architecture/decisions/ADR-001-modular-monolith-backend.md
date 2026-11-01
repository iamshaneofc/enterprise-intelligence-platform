# ADR-001: Modular Monolith Backend Architecture

## Status
ACCEPTED

## Context
The Enterprise Intelligence Platform requires a backend runtime capable of coordinating document ingestion, high-dimensional vector search, multi-provider LLM orchestration, multi-step autonomous AI agent workflows, conversational memory, and quantitative evaluation.

We need to choose between:
1. A distributed microservices architecture (e.g., separate ingestion service, RAG service, agent service, auth service).
2. A serverless / function-as-a-service (FaaS) architecture (e.g., AWS Lambda).
3. A modular monolith architecture organized by domain boundaries within a single codebase.

The architecture must support rapid developer velocity, high reliability, zero-friction local development, and straightforward modification during the 60-minute supervised live verification session.

## Decision
We adopt a **Modular Monolith** architecture implemented in **Python 3.11+** using **FastAPI** and **Pydantic v2**.

The codebase is organized into strict, decoupled layers:
- `app/api/`: Ingress HTTP routing, parameter extraction, and status code management.
- `app/schemas/`: Data transfer objects (DTOs) with runtime Pydantic validation.
- `app/services/`: Core business logic coordinating workflows across data and external providers.
- `app/repositories/`: Data access layer for relational database and vector queries.
- `app/models/`: SQLAlchemy 2.0 ORM database entity definitions.
- Specialized domain packages: `document_processing/`, `embeddings/`, `retrieval/`, `rag/`, `llm/`, `agents/`, `memory/`, `evaluation/`, and `workers/`.

## Alternatives Considered
- **Distributed Microservices:**
  - *Pros:* Independent scalability of ingestion vs. query workloads.
  - *Cons:* Substantial operational overhead (service discovery, distributed tracing, complex Docker Compose setup, network latency between hops, distributed transaction complexity). Inappropriate for a single-engineer assessment and impedes rapid live code modification.
- **Serverless (AWS Lambda):**
  - *Pros:* Auto-scaling, pay-per-request pricing.
  - *Cons:* Cold starts on heavy AI libraries, 15-minute execution limits on document parsing, complex local emulation, and bundle size constraints with dependencies like PyMuPDF.

## Rationale
FastAPI provides high-throughput asynchronous concurrency (ASGI), native Pydantic schema validation, and automatic OpenAPI documentation. Organizing the system as a modular monolith allows all domain modules to communicate via strongly-typed Python service interfaces with zero network serialization overhead. If scale requires decomposing a specific bottleneck (such as document extraction) into an independent service in the future, the modular package structure enables straightforward extraction without rewriting business logic.

## Consequences
- **Positive:**
  - Single deployable container simplifying cloud deployment.
  - Rapid local iteration and deterministic end-to-end debugging.
  - Complete code ownership and transparency for live technical verification.
  - High performance via Python `asyncio` for concurrent API and I/O operations.
- **Negative:**
  - Requires strict code discipline to avoid circular imports and tight cross-package coupling.
  - Scaling is coarse-grained (scaling the entire container rather than individual services).


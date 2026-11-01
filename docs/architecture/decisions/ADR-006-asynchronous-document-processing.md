# ADR-006: Asynchronous Document Processing with Redis Task Queue

## Status
ACCEPTED

## Context
Module A (Document Intelligence) and Challenge 6 (Asynchronous Document Processing) require uploading, validating, parsing, chunking, and indexing technical documents (`.pdf`, `.txt`, `.md`, `.csv`) without blocking synchronous HTTP API requests.

Technical documents—especially dense architecture diagrams or multi-page incident reports—can generate dozens of chunks requiring batch vector embeddings. Ingestion operations typically require 3 to 20 seconds. If executed synchronously within an HTTP request thread:
1. Web server worker threads are blocked from handling incoming user requests.
2. Ingress reverse proxies (Nginx, AWS ALB, Cloudflare) may terminate the connection with HTTP 504 Gateway Timeout.
3. The client browser UI hangs, degrading user experience.
4. If a timeout occurs, the client does not know whether ingestion succeeded or failed.

## Decision
We implement an **Asynchronous Document Processing Architecture** using **Redis 7** as the task broker and a **Dedicated Python Background Worker**:

1. **Immediate Ingress Response:**
   - The user uploads a file via `POST /api/v1/documents`.
   - The API server synchronously validates MIME magic bytes, size limits, computes the SHA-256 content hash, and checks for duplicates.
   - If unique, the server saves the raw file to object storage, creates a database record in PostgreSQL with status `PENDING`, pushes a job payload to the Redis task queue, and immediately returns HTTP `202 Accepted` with the `document_id`.
2. **Durable Worker Execution:**
   - The background worker dequeues the job.
   - Worker acquires a Redis distributed lock (`doc_lock:{content_hash}`) with a TTL to prevent concurrent duplicate processing of the same file.
   - Updates document status to `PROCESSING` in PostgreSQL.
   - Extracts text and structural metadata using PyMuPDF (PDF), CSV reader, or Markdown parser.
   - Executes recursive chunking (512-1024 tokens with 15% overlap).
   - Generates vector embeddings in batches via OpenAI `text-embedding-3-small`.
   - Atomically inserts chunks and vectors into PostgreSQL `document_chunks` (pgvector).
   - Updates document status to `INDEXED` and releases the Redis lock.
3. **Failure & Retry Handling:**
   - If an unhandled exception occurs (e.g., embedding API rate limit or corrupt PDF stream), the worker catches the error, increments a retry counter (max 3 retries with exponential backoff).
   - If retries are exhausted, the document status is updated to `FAILED`, the full stack trace is recorded in `documents.error_message`, and the lock is cleanly released.
4. **Client Polling / SSE Status Updates:**
   - The React frontend polls `GET /api/v1/documents/{id}/status` or listens to Server-Sent Events (SSE) to update the UI progress badge from "Processing" to "Indexed".

## Alternatives Considered
- **Synchronous In-Request Processing:**
  - *Pros:* Simple single-thread execution.
  - *Cons:* Directly causes gateway timeouts on large files; unacceptable in production environments.
- **FastAPI In-Memory `BackgroundTasks`:**
  - *Pros:* No external queue dependency.
  - *Cons:* Jobs run in the same process memory as the web server, blocking CPU cycles; tasks are completely lost if the web container restarts during deployment.
- **Celery with RabbitMQ:**
  - *Pros:* Enterprise-scale distributed task system.
  - *Cons:* Enormous configuration complexity, multiple daemon processes, excessive operational overhead for a 24-hour assessment.

## Rationale
Using Redis as the broker with an asynchronous worker provides production-grade isolation: heavy CPU parsing and network embedding requests never impact API response times. Furthermore, Redis is already utilized in the platform for session memory and query caching, adding zero new infrastructure dependencies.

## Consequences
- **Positive:**
  - Sub-100ms API response time on document upload (`HTTP 202 Accepted`).
  - Total resilience against reverse proxy timeouts.
  - Automatic retry mechanism for transient embedding API failures.
  - Redis distributed locking guarantees prevention of duplicate processing jobs.
- **Negative:**
  - Requires running a background worker process alongside the FastAPI web server.
  - Frontend must implement status polling or SSE connection to reflect indexing completion.


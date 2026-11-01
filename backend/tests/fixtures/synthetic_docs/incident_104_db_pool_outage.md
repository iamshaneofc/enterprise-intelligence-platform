# Incident 104 Postmortem: PostgreSQL Connection Pool Outage

## Metadata
- Incident ID: INC-104
- Severity: SEV-1
- Date: 2026-03-15
- Outage Start: 14:22 UTC
- Outage End: 14:58 UTC
- Primary Service: Accounts & Billing Service
- Database: Primary Aurora PostgreSQL Cluster (db-prod-primary)

## Executive Summary
On 2026-03-15 at 14:22 UTC, the PostgreSQL connection pool exhausted all 200 available connections.
This caused incoming HTTP requests to block indefinitely, resulting in widespread 504 Gateway Timeouts across the Accounts & Billing API.
The root cause was traced to an unindexed query on the `billing_ledger` table executed within an open transaction, combined with an idle connection leak.
The incident was mitigated by lowering the client connection acquisition timeout from 60s to 5s, terminating hanging queries, and scaling `max_connections` to 400.

## Timeline of Events
- 14:20 UTC: Background billing reconciliation cron job initiated a full table scan on `billing_ledger`.
- 14:22 UTC: Connection pool reached 100% capacity (200 / 200 connections in `active` state).
- 14:25 UTC: High latency alert triggered: P99 latency exceeded 12,000ms.
- 14:32 UTC: On-call engineer paged and acknowledged the incident.
- 14:40 UTC: Hanging backend transaction PIDs terminated via `pg_terminate_backend()`.
- 14:50 UTC: Configuration patched: `pool_timeout` lowered to 5s, `max_connections` increased to 400.
- 14:58 UTC: All service metrics returned to nominal baseline.

## Root Cause Analysis
1. Unindexed Sequential Scan: The query `SELECT * FROM billing_ledger WHERE account_id = $1 AND settlement_status = 'pending'` lacked a composite B-tree index on `(account_id, settlement_status)`.
2. Connection Leak: The Go database driver was holding open transactions during third-party payment gateway HTTP calls without a context deadline.

## Corrective Actions & Prevention
1. Deploy composite index on `billing_ledger (account_id, settlement_status)`.
2. Enforce strict 3-second context timeouts on all database transactions.
3. Add proactive connection pool saturation alert at 80% capacity (160 connections).


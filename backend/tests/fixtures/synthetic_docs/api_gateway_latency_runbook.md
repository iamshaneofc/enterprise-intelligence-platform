# Runbook: API Gateway High Latency and 504 Timeout Remediation

## Overview
This runbook guides on-call engineers when handling elevated latency alerts or 504 Gateway Timeout responses from the Envoy API Gateway edge proxies.

## Diagnostic Steps
1. Verify Gateway Health:
   - Check Envoy upstream cluster status using `/stats/prometheus` endpoint.
   - Inspect `upstream_rq_time` 99th percentile metric. Normal baseline is < 150ms.
2. Identify Degraded Upstream:
   - Run: `kubectl logs -l app=envoy-gateway -n ingress --tail=500 | grep "504"`
   - Isolate the upstream service experiencing queue backups (e.g., `accounts-svc`, `search-svc`).
3. Check Upstream Worker Thread Saturation:
   - Inspect CPU and memory utilization on upstream pods. If CPU exceeds 85%, horizontal pod autoscaler (HPA) must trigger.
   - If upstream latency exceeds 4200ms, enable Envoy circuit breaking to drop excess traffic gracefully.

## Mitigation Procedures
1. Apply Rate Limiting:
   - Throttle abusive caller IP addresses or API keys using Envoy token bucket filters.
2. Shed Traffic with Circuit Breakers:
   - Configure max pending requests: `max_pending_requests: 100`.
   - Configure max concurrent requests: `max_requests: 1024`.
3. Restart Hanging Upstream Replicas:
   - Execute rolling restart: `kubectl rollout restart deployment/<degraded-service> -n production`.


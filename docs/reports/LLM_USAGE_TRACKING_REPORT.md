# Standardized LLM Usage Tracking Report
**Engineering Intelligence Platform (EIP)**  
**Date:** November 2026  
**Status:** Completed & Empirically Validated  

---

## 1. Executive Summary

This report documents the implementation of standardized, tenant-isolated LLM usage tracking and telemetry for the Engineering Intelligence Platform (EIP).

Key improvements implemented:
1. **Typed Event Schema:** Introduced `LLMUsageEvent` Pydantic schema in `backend/app/schemas/telemetry.py`.
2. **Database Persistence & Migration:** Added `session_id`, `cached_prompt_tokens`, and `error_type` to `llm_logs` table via SQLAlchemy model updates and Alembic migration `58f1a23b49de`.
3. **Accurate Token Accounting Without Double-Counting:** Retries and fallback failures are accurately logged as distinct `status="error"` telemetry events without duplicating token counts or inflating financial usage metrics.
4. **Prompt Caching Extraction:** Integrated prompt caching extraction across Anthropic (`cache_read_input_tokens`) and OpenAI (`prompt_tokens_details.cached_tokens`).

---

## 2. Schema Specification

### A. Pydantic Event Schema: `LLMUsageEvent`

```python
class LLMUsageEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    workspace_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_prompt_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    is_fallback: bool = False
    status: Literal["success", "error", "throttled"] = "success"
    error_type: Optional[str] = None
```

### B. Database Schema: `llm_logs`

| Column | Type | Nullable | Description |
|:---|:---|:---:|:---|
| `id` | VARCHAR(36) | No | Primary Key (UUID) |
| `workspace_id` | VARCHAR(36) | Yes | Workspace / Tenant ID (Indexed) |
| `user_id` | VARCHAR(36) | Yes | Authenticated user ID (Indexed) |
| `session_id` | VARCHAR(36) | Yes | Conversation / Chat Session ID (Indexed) |
| `provider` | VARCHAR(50) | No | Provider name (`anthropic`, `openai`, `fake`) |
| `model` | VARCHAR(100) | No | Model ID (`claude-3-5-sonnet-20241022`, `gpt-4o`) |
| `prompt_tokens` | INTEGER | No | Input tokens billed |
| `completion_tokens` | INTEGER | No | Output tokens generated |
| `cached_prompt_tokens` | INTEGER | Yes | Prompt tokens served from cache |
| `total_tokens` | INTEGER | No | Sum of prompt and completion tokens |
| `latency_ms` | INTEGER | No | Round-trip provider latency in milliseconds |
| `cost_usd` | FLOAT | No | Computed financial cost based on `LLM_PRICING` |
| `is_fallback` | BOOLEAN | No | True if served via circuit-breaker fallback |
| `status` | VARCHAR(50) | No | `success`, `error`, or `throttled` |
| `error_type` | VARCHAR(100) | Yes | Exception class name on failure |
| `created_at` | DATETIME | No | UTC timestamp |

---

## 3. Provider Token Extraction Logic

### Anthropic Claude 3.5 Sonnet
In `backend/app/llm/anthropic_client.py`:
```python
prompt_tokens = resp.usage.input_tokens
completion_tokens = resp.usage.output_tokens
cached_prompt_tokens = getattr(resp.usage, "cache_read_input_tokens", 0) or 0
```

### OpenAI GPT-4o
In `backend/app/llm/openai_client.py`:
```python
prompt_tokens = usage.prompt_tokens if usage else 0
completion_tokens = usage.completion_tokens if usage else 0
prompt_details = getattr(usage, "prompt_tokens_details", None)
cached_prompt_tokens = getattr(prompt_details, "cached_tokens", 0) if prompt_details else 0
```

---

## 4. Double-Counting Prevention in Failover Scenarios

When a primary provider encounters a transient failure (e.g. RateLimit 429 or 503 Overloaded) and triggers secondary failover:
1. **Primary Attempt:** An audit event is recorded with `status="error"`, `error_type=type(e).__name__`, `completion_tokens=0`, and `cost_usd=0.0`.
2. **Fallback Attempt:** The secondary provider executes. Upon completion, a separate event is recorded with `status="success"`, `is_fallback=True`, and actual tokens/cost.
3. **Billing Aggregate Safety:** Any billing aggregation query (`SUM(cost_usd)`, `SUM(total_tokens) WHERE status = 'success'`) never double-counts the failed primary request.

---

## 5. Verification & Unit Tests

The usage tracking implementation was validated via `backend/tests/unit/test_usage_tracking.py`:

```
============================= test session starts =============================
platform win32 -- Python 3.14.2, pytest-9.1.1, pluggy-1.6.0
collected 3 items

backend/tests/unit/test_usage_tracking.py::test_llm_usage_event_schema_defaults PASSED [ 33%]
backend/tests/unit/test_usage_tracking.py::test_router_usage_logging_persistence PASSED [ 66%]
backend/tests/unit/test_usage_tracking.py::test_router_fallback_logging_without_double_counting PASSED [100%]

============================== 3 passed in 0.20s ==============================
```


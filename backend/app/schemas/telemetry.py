"""Telemetry and standardized LLM usage schemas for observability."""
import uuid
from datetime import datetime, timezone
from typing import Optional, Literal
from pydantic import BaseModel, Field


class LLMUsageEvent(BaseModel):
    """Standardized event emitted for LLM invocation attempts, token counting, and cost tracking."""
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


"""LLM Provider Usage & Observability Log database model."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime

from backend.app.db.session import Base


class LLMLog(Base):
    __tablename__ = "llm_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String(36), nullable=True, index=True)
    user_id = Column(String(36), nullable=True, index=True)
    provider = Column(String(50), nullable=False)  # anthropic, openai, fake
    model = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, default=0, nullable=False)
    completion_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)
    latency_ms = Column(Integer, default=0, nullable=False)
    cost_usd = Column(Float, default=0.0, nullable=False)
    is_fallback = Column(Boolean, default=False, nullable=False)
    status = Column(String(50), default="success", nullable=False)  # success, error, throttled
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


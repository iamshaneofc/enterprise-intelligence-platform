"""Tests for standardized LLM usage tracking and telemetry."""
import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal
from backend.app.models.llm_log import LLMLog
from backend.app.schemas.telemetry import LLMUsageEvent
from backend.app.llm.base import LLMMessage, LLMResponse
from backend.app.llm.fake_client import FakeLLMClient
from backend.app.llm.router import LLMFallbackRouter


def test_llm_usage_event_schema_defaults():
    """Verify LLMUsageEvent creates valid unique IDs and timestamps."""
    event = LLMUsageEvent(
        provider="anthropic",
        model="claude-3-5-sonnet-20241022",
        prompt_tokens=150,
        completion_tokens=50,
        cached_prompt_tokens=25,
        total_tokens=200,
        cost_usd=0.0012,
        latency_ms=250,
        status="success",
    )
    assert event.event_id is not None
    assert isinstance(event.timestamp, datetime)
    assert event.cached_prompt_tokens == 25
    assert event.is_fallback is False
    assert event.status == "success"


def test_router_usage_logging_persistence():
    """Verify router logs LLMUsageEvent to the database upon generation."""
    db: Session = SessionLocal()
    try:
        fake_client = FakeLLMClient(model="fake-test-model", provider="fake_prov")
        router = LLMFallbackRouter(primary_client=fake_client, fallback_client=fake_client)

        messages = [LLMMessage(role="user", content="Ping healthcheck")]
        resp = router.generate(
            messages=messages,
            workspace_id="test-ws-uuid",
            user_id="test-user-uuid",
            session_id="test-session-uuid",
            db=db,
        )

        assert resp is not None
        # Verify row persisted in database
        log_entry = db.query(LLMLog).filter(LLMLog.session_id == "test-session-uuid").first()
        assert log_entry is not None
        assert log_entry.provider == "fake_prov"
        assert log_entry.model == "fake-test-model"
        assert log_entry.workspace_id == "test-ws-uuid"
        assert log_entry.user_id == "test-user-uuid"
        assert log_entry.status == "success"
        assert log_entry.is_fallback is False
    finally:
        db.close()


def test_router_fallback_logging_without_double_counting():
    """Verify fallback logs failure on primary and success on fallback cleanly."""
    db: Session = SessionLocal()
    try:
        # Primary client configured to fail
        failing_primary = FakeLLMClient(model="failing-model", provider="primary_prov", force_fail=True)
        working_fallback = FakeLLMClient(model="fallback-model", provider="fallback_prov")

        router = LLMFallbackRouter(primary_client=failing_primary, fallback_client=working_fallback)

        test_session_id = f"fallback-session-{datetime.now().timestamp()}"
        messages = [LLMMessage(role="user", content="Test fallback logging")]

        resp = router.generate(
            messages=messages,
            workspace_id="ws-fallback-test",
            user_id="usr-fallback-test",
            session_id=test_session_id,
            db=db,
        )

        assert resp.is_fallback is True
        assert resp.provider == "fallback_prov"

        # Check logs in DB for this session
        logs = db.query(LLMLog).filter(LLMLog.session_id == test_session_id).order_by(LLMLog.created_at.asc()).all()
        # Exactly 1 log entry is stored for the completed invocation, preventing double-counting
        assert len(logs) == 1

        fallback_log = logs[0]
        assert fallback_log.provider == "fallback_prov"
        assert fallback_log.status == "success"
        assert fallback_log.is_fallback is True
        assert fallback_log.completion_tokens > 0

    finally:
        db.close()

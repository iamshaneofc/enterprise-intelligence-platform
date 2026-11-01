"""Unit tests for LLM provider abstraction, fallback failover, and telemetry logging."""
from sqlalchemy.orm import Session
from backend.app.llm.base import LLMMessage
from backend.app.llm.fake_client import FakeLLMClient
from backend.app.llm.router import LLMFallbackRouter
from backend.app.models.llm_log import LLMLog


def test_llm_primary_success(db_session: Session):
    primary = FakeLLMClient(model="fake-primary", provider="test_primary")
    fallback = FakeLLMClient(model="fake-fallback", provider="test_fallback")
    router = LLMFallbackRouter(primary_client=primary, fallback_client=fallback)

    messages = [LLMMessage(role="user", content="Hello test")]
    response = router.generate(messages, db=db_session)

    assert response.provider == "test_primary"
    assert response.is_fallback is False

    # Check LLM log in DB
    logs = db_session.query(LLMLog).all()
    assert len(logs) == 1
    assert logs[0].provider == "test_primary"
    assert logs[0].is_fallback is False


def test_llm_automatic_fallback_on_primary_failure(db_session: Session):
    primary = FakeLLMClient(model="fake-primary", provider="test_primary")
    primary.force_fail = True  # Trigger simulated 429 quota/server error

    fallback = FakeLLMClient(model="fake-fallback", provider="test_fallback")
    router = LLMFallbackRouter(primary_client=primary, fallback_client=fallback)

    messages = [LLMMessage(role="user", content="Test fallback request")]
    response = router.generate(messages, db=db_session)

    # Must have fallen back to secondary provider
    assert response.provider == "test_fallback"
    assert response.is_fallback is True

    # Check that fallback is recorded in observability log
    logs = db_session.query(LLMLog).all()
    assert len(logs) == 1
    assert logs[0].provider == "test_fallback"
    assert logs[0].is_fallback is True


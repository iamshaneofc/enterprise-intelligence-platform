"""Tests for Langfuse observability instrumentation and fail-safe operation."""
import os
import pytest
from unittest.mock import patch

from backend.app.observability.langfuse_tracer import (
    is_langfuse_configured,
    observe,
    flush_langfuse,
)


def test_langfuse_unconfigured_by_default():
    """Verify that when no API keys are provided, Langfuse is disabled."""
    with patch.dict(os.environ, {}, clear=True):
        assert is_langfuse_configured() is False


def test_observe_decorator_passthrough_when_disabled():
    """Verify that observe acts as a transparent zero-overhead passthrough when disabled."""
    call_count = 0

    @observe(name="test_span", as_type="generation")
    def sample_func(a: int, b: int) -> int:
        nonlocal call_count
        call_count += 1
        return a + b

    # Execution should succeed without any error
    result = sample_func(10, 20)
    assert result == 30
    assert call_count == 1


def test_observe_decorator_with_keyword_arguments():
    """Verify observe passes all kwargs cleanly."""
    @observe(name="kw_span")
    def kw_func(x: str, multiplier: int = 2) -> str:
        return x * multiplier

    assert kw_func("hello", multiplier=3) == "hellohellohello"


def test_flush_langfuse_safe_noop():
    """Verify flush_langfuse does not raise any exception when disabled."""
    flush_langfuse()  # Must not raise


def test_langfuse_configured_detection():
    """Verify is_langfuse_configured detects valid credentials."""
    with patch.dict(os.environ, {
        "LANGFUSE_PUBLIC_KEY": "pk-lf-test-12345",
        "LANGFUSE_SECRET_KEY": "sk-lf-test-67890",
    }):
        assert is_langfuse_configured() is True


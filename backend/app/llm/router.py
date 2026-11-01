"""LLM Router with automatic circuit breaker fallback and observability logging."""
from typing import List, Optional, Type
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.core.exceptions import LLMProviderError, LLMQuotaExceededError
from backend.app.llm.base import BaseLLMClient, LLMMessage, LLMResponse
from backend.app.llm.fake_client import FakeLLMClient
from backend.app.models.llm_log import LLMLog
from backend.app.schemas.telemetry import LLMUsageEvent
from backend.app.observability.langfuse_tracer import observe
from pydantic import BaseModel


def is_retryable_error(error: Exception) -> bool:
    """Determine if an error is retryable (transient failure)."""
    # Check for specific retryable exception types
    error_type = type(error).__name__
    retryable_types = {
        "RateLimitError",
        "APITimeoutError", 
        "APIConnectionError",
        "TimeoutError",
        "ConnectionError",
    }
    if error_type in retryable_types:
        return True
    
    # Check for APIStatusError with 5xx status
    if hasattr(error, "status_code"):
        status_code = getattr(error, "status_code", 0)
        if status_code >= 500:
            return True
        # 429 is rate limit (already handled by RateLimitError)
        if status_code == 429:
            return True
        # Other 4xx errors are not retryable
        return False
    
    # Check error message for transient indicators
    error_msg = str(error).lower()
    transient_indicators = [
        "timeout",
        "connection",
        "rate limit",
        "rate_limit",
        "temporarily unavailable",
        "service unavailable",
        "gateway timeout",
        "upstream timeout",
    ]
    if any(indicator in error_msg for indicator in transient_indicators):
        return True
    
    return False


def is_fallback_error(error: Exception) -> bool:
    """Determine if an error should trigger fallback to secondary provider."""
    # Only fallback on retryable errors from the primary provider
    return is_retryable_error(error)


class LLMFallbackRouter:
    """Manages primary LLM execution and seamless failover to fallback provider."""

    def __init__(
        self,
        primary_client: Optional[BaseLLMClient] = None,
        fallback_client: Optional[BaseLLMClient] = None,
    ):
        self._primary = primary_client
        self._fallback = fallback_client

    def _get_primary(self) -> BaseLLMClient:
        if self._primary:
            return self._primary
        if settings.USE_FAKE_LLM or not settings.ANTHROPIC_API_KEY:
            return FakeLLMClient(model="fake-claude-3-5-sonnet", provider="fake_primary")
        from backend.app.llm.anthropic_client import AnthropicClient
        return AnthropicClient()

    def _get_fallback(self) -> BaseLLMClient:
        if self._fallback:
            return self._fallback
        if settings.USE_FAKE_LLM or not settings.OPENAI_API_KEY:
            return FakeLLMClient(model="fake-gpt-4o", provider="fake_fallback")
        from backend.app.llm.openai_client import OpenAIClient
        return OpenAIClient()

    def _calculate_cost(self, provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost based on model pricing."""
        provider_pricing = settings.LLM_PRICING.get(provider.lower(), {})
        model_pricing = provider_pricing.get(model, {})
        prompt_cost = model_pricing.get("prompt", 0) * (prompt_tokens / 1000)
        completion_cost = model_pricing.get("completion", 0) * (completion_tokens / 1000)
        return round(prompt_cost + completion_cost, 6)

    @observe(as_type="generation", name="llm_generation")
    def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        max_tokens: int = 2048,
        workspace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> LLMResponse:
        """Execute LLM call with primary provider and automatic fallback on retryable errors."""
        primary = self._get_primary()
        fallback = self._get_fallback()

        response: Optional[LLMResponse] = None
        is_fallback = False
        error_msg: Optional[str] = None

        try:
            response = primary.generate(messages, temperature=temperature, max_tokens=max_tokens)
        except Exception as e:
            # Only fallback on retryable/transient errors
            if is_fallback_error(e):
                logger.warning(f"Primary LLM provider failed with retryable error ({str(e)}). Initiating fallback to secondary provider...")
                is_fallback = True
                try:
                    response = fallback.generate(messages, temperature=temperature, max_tokens=max_tokens)
                    response.is_fallback = True
                except Exception as fe:
                    if is_fallback_error(fe):
                        logger.error(f"Fallback provider also failed with retryable error: {str(fe)}")
                    error_msg = f"Both primary and fallback LLM providers failed. Fallback error: {str(fe)}"
                    logger.error(error_msg)
                    raise LLMProviderError(error_msg)
            else:
                logger.warning(f"Primary LLM provider failed with non-retryable error: {str(e)}")
                raise

        # Record LLM observability log in DB if session provided
        if db and response:
            try:
                cost = self._calculate_cost(
                    response.provider, response.model,
                    response.prompt_tokens, response.completion_tokens
                )
                usage_event = LLMUsageEvent(
                    workspace_id=workspace_id,
                    user_id=user_id,
                    session_id=session_id,
                    provider=response.provider,
                    model=response.model,
                    prompt_tokens=response.prompt_tokens,
                    completion_tokens=response.completion_tokens,
                    cached_prompt_tokens=getattr(response, "cached_prompt_tokens", 0),
                    total_tokens=response.total_tokens,
                    latency_ms=response.latency_ms,
                    cost_usd=cost,
                    is_fallback=response.is_fallback,
                    status="success",
                )
                log_entry = LLMLog(
                    id=usage_event.event_id,
                    workspace_id=usage_event.workspace_id,
                    user_id=usage_event.user_id,
                    session_id=usage_event.session_id,
                    provider=usage_event.provider,
                    model=usage_event.model,
                    prompt_tokens=usage_event.prompt_tokens,
                    completion_tokens=usage_event.completion_tokens,
                    cached_prompt_tokens=usage_event.cached_prompt_tokens,
                    total_tokens=usage_event.total_tokens,
                    latency_ms=usage_event.latency_ms,
                    cost_usd=usage_event.cost_usd,
                    is_fallback=usage_event.is_fallback,
                    status=usage_event.status,
                )
                db.add(log_entry)
                db.commit()
            except Exception as log_err:
                logger.warning(f"Failed to record LLM log entry: {log_err}")

        return response


llm_router = LLMFallbackRouter()


@observe(as_type="generation", name="llm_generate_structured")
def generate_structured(
    messages: List[LLMMessage],
    response_model: Type[BaseModel],
    temperature: float = 0.0,
    max_tokens: int = 2048,
    workspace_id: Optional[str] = None,
    user_id: Optional[str] = None,
    db: Optional[Session] = None,
) -> BaseModel:
    """
    Generate structured output using the LLM router with fallback.
    
    Args:
        messages: Conversation messages
        response_model: Pydantic model class to validate response against
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        workspace_id: Optional workspace ID for logging
        user_id: Optional user ID for logging
        db: Optional database session for logging
        
    Returns:
        Validated Pydantic model instance
        
    Raises:
        ValidationError: If response doesn't match schema
        LLMProviderError: If generation fails
    """
    primary = llm_router._get_primary()
    fallback = llm_router._get_fallback()

    # Try primary provider first
    try:
        return primary.generate_structured(messages, response_model, temperature, max_tokens)
    except Exception as e:
        if is_fallback_error(e):
            logger.warning(f"Primary LLM provider failed with retryable error ({str(e)}). Initiating fallback to secondary provider...")
            try:
                result = fallback.generate_structured(messages, response_model, temperature, max_tokens)
                return result
            except Exception as fe:
                if is_fallback_error(fe):
                    logger.error(f"Fallback provider also failed with retryable error: {str(fe)}")
                error_msg = f"Both primary and fallback LLM providers failed. Fallback error: {str(fe)}"
                logger.error(error_msg)
                raise LLMProviderError(error_msg)
        else:
            logger.warning(f"Primary LLM provider failed with non-retryable error: {str(e)}")
            raise


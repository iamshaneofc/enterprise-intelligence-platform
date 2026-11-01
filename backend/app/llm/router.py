"""LLM Router with automatic circuit breaker fallback and observability logging."""
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.core.exceptions import LLMProviderError, LLMQuotaExceededError
from backend.app.llm.base import BaseLLMClient, LLMMessage, LLMResponse
from backend.app.llm.fake_client import FakeLLMClient
from backend.app.models.llm_log import LLMLog


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

    def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        max_tokens: int = 2048,
        workspace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> LLMResponse:
        """Execute LLM call with primary provider and automatic fallback on errors."""
        primary = self._get_primary()
        fallback = self._get_fallback()

        response: Optional[LLMResponse] = None
        is_fallback = False
        error_msg: Optional[str] = None

        try:
            response = primary.generate(messages, temperature=temperature, max_tokens=max_tokens)
        except (LLMQuotaExceededError, LLMProviderError, Exception) as e:
            logger.warning(f"Primary LLM provider failed ({str(e)}). Initiating fallback to secondary provider...")
            is_fallback = True
            try:
                response = fallback.generate(messages, temperature=temperature, max_tokens=max_tokens)
                response.is_fallback = True
            except Exception as fe:
                error_msg = f"Both primary and fallback LLM providers failed. Fallback error: {str(fe)}"
                logger.error(error_msg)
                raise LLMProviderError(error_msg)

        # Record LLM observability log in DB if session provided
        if db and response:
            try:
                cost = self._calculate_cost(
                    response.provider, response.model,
                    response.prompt_tokens, response.completion_tokens
                )
                log_entry = LLMLog(
                    workspace_id=workspace_id,
                    user_id=user_id,
                    provider=response.provider,
                    model=response.model,
                    prompt_tokens=response.prompt_tokens,
                    completion_tokens=response.completion_tokens,
                    total_tokens=response.total_tokens,
                    latency_ms=response.latency_ms,
                    cost_usd=cost,
                    is_fallback=response.is_fallback,
                    status="success",
                )
                db.add(log_entry)
                db.commit()
            except Exception as log_err:
                logger.warning(f"Failed to record LLM log entry: {log_err}")

        return response


llm_router = LLMFallbackRouter()


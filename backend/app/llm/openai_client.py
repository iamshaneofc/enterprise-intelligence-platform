"""OpenAI LLM provider implementation."""
import time
from typing import List, Optional
from backend.app.core.config import settings
from backend.app.core.exceptions import LLMProviderError, LLMQuotaExceededError
from backend.app.core.logging import logger
from backend.app.llm.base import BaseLLMClient, LLMMessage, LLMResponse


class OpenAIClient(BaseLLMClient):
    """Client for OpenAI GPT-4o / GPT-4o-mini."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.FALLBACK_LLM_MODEL
        if not self.api_key:
            raise LLMProviderError("OpenAI API key is not configured")
        
        import openai
        self.client = openai.OpenAI(api_key=self.api_key)

    def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        import openai
        start_time = time.time()
        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            latency_ms = int((time.time() - start_time) * 1000)

            choice = resp.choices[0]
            content = choice.message.content or ""
            usage = resp.usage
            prompt_tokens = usage.prompt_tokens if usage else 0
            completion_tokens = usage.completion_tokens if usage else 0

            return LLMResponse(
                content=content,
                model=self.model,
                provider="openai",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                latency_ms=latency_ms,
                is_fallback=False,
                raw_response=resp,
            )
        except openai.RateLimitError as e:
            raise LLMQuotaExceededError(f"OpenAI rate limit exceeded: {str(e)}")
        except Exception as e:
            raise LLMProviderError(f"OpenAI generation error: {str(e)}")


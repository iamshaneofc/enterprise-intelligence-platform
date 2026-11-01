"""Anthropic Claude LLM provider implementation."""
import time
from typing import List, Optional
from backend.app.core.config import settings
from backend.app.core.exceptions import LLMProviderError, LLMQuotaExceededError
from backend.app.core.logging import logger
from backend.app.llm.base import BaseLLMClient, LLMMessage, LLMResponse


class AnthropicClient(BaseLLMClient):
    """Client for Anthropic Claude 3.5 Sonnet / Haiku."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.PRIMARY_LLM_MODEL
        if not self.api_key:
            raise LLMProviderError("Anthropic API key is not configured")
        
        import anthropic
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        import anthropic
        start_time = time.time()
        
        # Anthropic separates system messages from conversation messages
        system_prompt = ""
        user_assistant_messages = []
        for m in messages:
            if m.role == "system":
                system_prompt += f"{m.content}\n"
            else:
                user_assistant_messages.append({"role": m.role, "content": m.content})

        try:
            kwargs = {
                "model": self.model,
                "messages": user_assistant_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if system_prompt:
                kwargs["system"] = system_prompt.strip()

            resp = self.client.messages.create(**kwargs)
            latency_ms = int((time.time() - start_time) * 1000)

            content = resp.content[0].text if resp.content else ""
            prompt_tokens = resp.usage.input_tokens
            completion_tokens = resp.usage.output_tokens

            return LLMResponse(
                content=content,
                model=self.model,
                provider="anthropic",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                latency_ms=latency_ms,
                is_fallback=False,
                raw_response=resp,
            )
        except anthropic.RateLimitError as e:
            raise LLMQuotaExceededError(f"Anthropic rate limit exceeded: {str(e)}")
        except Exception as e:
            raise LLMProviderError(f"Anthropic generation error: {str(e)}")


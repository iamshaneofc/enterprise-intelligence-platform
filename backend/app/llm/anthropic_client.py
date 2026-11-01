"""Anthropic Claude LLM provider implementation."""
import time
from typing import List, Optional
from backend.app.core.config import settings
from backend.app.core.exceptions import LLMProviderError, LLMQuotaExceededError
from backend.app.core.logging import logger
from backend.app.llm.base import BaseLLMClient, LLMMessage, LLMResponse


class AnthropicClient(BaseLLMClient):
    """Client for Anthropic Claude 3.5 Sonnet / Haiku."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: int = 2,
    ):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.PRIMARY_LLM_MODEL
        if not self.api_key:
            raise LLMProviderError("Anthropic API key is not configured")
        
        self.timeout = timeout or settings.LLM_REQUEST_TIMEOUT
        self.max_retries = max_retries

        import anthropic
        self.client = anthropic.Anthropic(
            api_key=self.api_key,
            timeout=self.timeout,
            max_retries=0,  # We handle retries ourselves
        )

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

        last_exception = None
        for attempt in range(self.max_retries + 1):
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
                cached_prompt_tokens = getattr(resp.usage, "cache_read_input_tokens", 0) or 0

                return LLMResponse(
                    content=content,
                    model=self.model,
                    provider="anthropic",
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cached_prompt_tokens=cached_prompt_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    latency_ms=latency_ms,
                    is_fallback=False,
                    raw_response=resp,
                )
            except anthropic.RateLimitError as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = (2 ** attempt) * 1.0
                    logger.warning(f"Anthropic rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    continue
                raise LLMQuotaExceededError(f"Anthropic rate limit exceeded: {str(e)}")
            except anthropic.APITimeoutError as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = (2 ** attempt) * 1.0
                    logger.warning(f"Anthropic timeout, retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    continue
                raise LLMProviderError(f"Anthropic request timeout: {str(e)}")
            except anthropic.APIConnectionError as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = (2 ** attempt) * 1.0
                    logger.warning(f"Anthropic connection error, retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    continue
                raise LLMProviderError(f"Anthropic connection error: {str(e)}")
            except anthropic.APIStatusError as e:
                # 5xx errors are retryable, 4xx (except 429) are not
                if e.status_code >= 500:
                    last_exception = e
                    if attempt < self.max_retries:
                        wait_time = (2 ** attempt) * 1.0
                        logger.warning(f"Anthropic server error ({e.status_code}), retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})")
                        time.sleep(wait_time)
                        continue
                raise LLMProviderError(f"Anthropic API error ({e.status_code}): {str(e)}")
            except Exception as e:
                # Non-retryable errors (invalid input, auth errors, etc.)
                raise LLMProviderError(f"Anthropic generation error: {str(e)}")
        
        # If we exhausted retries
        raise LLMProviderError(f"Anthropic generation failed after {self.max_retries + 1} attempts: {str(last_exception)}")


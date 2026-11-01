"""OpenAI LLM provider implementation."""
import time
from typing import List, Optional
from backend.app.core.config import settings
from backend.app.core.exceptions import LLMProviderError, LLMQuotaExceededError
from backend.app.core.logging import logger
from backend.app.llm.base import BaseLLMClient, LLMMessage, LLMResponse


class OpenAIClient(BaseLLMClient):
    """Client for OpenAI GPT-4o / GPT-4o-mini."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: int = 2,
    ):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.FALLBACK_LLM_MODEL
        if not self.api_key:
            raise LLMProviderError("OpenAI API key is not configured")
        
        self.timeout = timeout or settings.LLM_REQUEST_TIMEOUT
        self.max_retries = max_retries

        import openai
        self.client = openai.OpenAI(
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
        import openai
        start_time = time.time()
        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]

        last_exception = None
        for attempt in range(self.max_retries + 1):
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
                prompt_details = getattr(usage, "prompt_tokens_details", None)
                cached_prompt_tokens = getattr(prompt_details, "cached_tokens", 0) if prompt_details else 0

                return LLMResponse(
                    content=content,
                    model=self.model,
                    provider="openai",
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cached_prompt_tokens=cached_prompt_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    latency_ms=latency_ms,
                    is_fallback=False,
                    raw_response=resp,
                )
            except openai.RateLimitError as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = (2 ** attempt) * 1.0  # Exponential backoff: 1s, 2s, 4s...
                    logger.warning(f"OpenAI rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    continue
                raise LLMQuotaExceededError(f"OpenAI rate limit exceeded: {str(e)}")
            except openai.APITimeoutError as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = (2 ** attempt) * 1.0
                    logger.warning(f"OpenAI timeout, retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    continue
                raise LLMProviderError(f"OpenAI request timeout: {str(e)}")
            except openai.APIConnectionError as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = (2 ** attempt) * 1.0
                    logger.warning(f"OpenAI connection error, retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    continue
                raise LLMProviderError(f"OpenAI connection error: {str(e)}")
            except openai.APIStatusError as e:
                # 5xx errors are retryable, 4xx (except 429) are not
                if e.status_code >= 500:
                    last_exception = e
                    if attempt < self.max_retries:
                        wait_time = (2 ** attempt) * 1.0
                        logger.warning(f"OpenAI server error ({e.status_code}), retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})")
                        time.sleep(wait_time)
                        continue
                raise LLMProviderError(f"OpenAI API error ({e.status_code}): {str(e)}")
            except Exception as e:
                # Non-retryable errors (invalid input, auth errors, etc.)
                raise LLMProviderError(f"OpenAI generation error: {str(e)}")
        
        # If we exhausted retries
        raise LLMProviderError(f"OpenAI generation failed after {self.max_retries + 1} attempts: {str(last_exception)}")


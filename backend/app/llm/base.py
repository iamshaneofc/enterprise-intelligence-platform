"""Abstract interfaces and data structures for LLM providers."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Type
from pydantic import BaseModel


@dataclass
class LLMMessage:
    """Standardized message format for LLM conversation context."""
    role: str  # system, user, assistant
    content: str


@dataclass
class LLMResponse:
    """Standardized response format across Anthropic, OpenAI, and test providers."""
    content: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    is_fallback: bool = False
    raw_response: Optional[Any] = None


class BaseLLMClient(ABC):
    """Abstract interface for LLM client implementations."""

    @abstractmethod
    def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Generate text completion from conversation messages."""
        pass


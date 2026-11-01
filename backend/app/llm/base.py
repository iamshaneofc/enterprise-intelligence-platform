"""Abstract interfaces and data structures for LLM providers."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Type
from pydantic import BaseModel, ValidationError
import json


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
    cached_prompt_tokens: int = 0
    is_fallback: bool = False
    raw_response: Optional[Any] = None


class StructuredOutputError(Exception):
    """Raised when structured output validation fails."""
    pass


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

    def generate_structured(
        self,
        messages: List[LLMMessage],
        response_model: Type[BaseModel],
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> BaseModel:
        """
        Generate structured output validated against a Pydantic model.
        
        Args:
            messages: Conversation messages
            response_model: Pydantic model class to validate response against
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Validated Pydantic model instance
            
        Raises:
            StructuredOutputError: If response doesn't match schema
            LLMProviderError: If generation fails
        """
        # Add instruction for structured output
        structured_messages = list(messages)
        schema = response_model.model_json_schema()
        structured_messages.append(LLMMessage(
            role="system",
            content=f"Respond with valid JSON matching this schema: {schema}. No additional text."
        ))
        
        response = self.generate(structured_messages, temperature=0.0, max_tokens=max_tokens)
        
        try:
            # Try to parse JSON from response
            # Try to extract JSON from response (handle markdown code blocks)
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            data = json.loads(content)
            return response_model(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise StructuredOutputError(f"Failed to parse structured response: {str(e)}")


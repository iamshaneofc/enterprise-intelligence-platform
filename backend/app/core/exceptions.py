"""Custom enterprise application exceptions."""
from typing import Any, Dict, Optional


class EIPException(Exception):
    """Base exception for all Enterprise Intelligence Platform errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class EntityNotFoundError(EIPException):
    """Raised when a requested resource does not exist."""
    pass


class DuplicateEntityError(EIPException):
    """Raised when creating an entity that violates uniqueness."""
    pass


class AuthenticationError(EIPException):
    """Raised when authentication fails."""
    pass


class PermissionDeniedError(EIPException):
    """Raised when an authenticated user lacks authorization."""
    pass


class DocumentProcessingError(EIPException):
    """Raised when document ingestion, parsing, or chunking fails."""
    pass


class LLMProviderError(EIPException):
    """Raised when an external or local LLM call fails."""
    pass


class LLMQuotaExceededError(LLMProviderError):
    """Raised when rate limits or quotas are hit (429)."""
    pass


class AgentExecutionError(EIPException):
    """Raised when an autonomous agent encounters an unrecoverable error."""
    pass


class GroundingCheckFailedError(EIPException):
    """Raised when RAG output contains ungrounded claims or hallucinated references."""
    pass


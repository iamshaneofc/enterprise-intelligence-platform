"""Langfuse Observability & Tracing Instrumentation for EIP.

Provides fail-safe, non-blocking telemetry decorators for RAG pipelines,
retrieval algorithms, LLM generations, and autonomous agents.

Guarantees:
- Zero-cost pass-through when Langfuse is not configured or disabled.
- Zero exceptions / crashes if Langfuse network endpoints are unreachable.
- Automatic integration with Langfuse v5 SDK.
"""
import functools
import logging
import os
from typing import Callable, Any, Optional, Dict

logger = logging.getLogger(__name__)

# Check Langfuse SDK availability
_LANGFUSE_AVAILABLE = False

try:
    import langfuse
    _LANGFUSE_AVAILABLE = True
except Exception as e:
    logger.debug(f"Langfuse SDK unavailable: {e}")


def is_langfuse_configured() -> bool:
    """Return True only if Langfuse is available and credentials are provided."""
    if not _LANGFUSE_AVAILABLE:
        return False
    
    # Read from environment or settings
    from backend.app.core.config import settings
    pub_key = os.getenv("LANGFUSE_PUBLIC_KEY") or settings.LANGFUSE_PUBLIC_KEY
    sec_key = os.getenv("LANGFUSE_SECRET_KEY") or settings.LANGFUSE_SECRET_KEY
    explicit_flag = os.getenv("LANGFUSE_ENABLED", "").lower() in ("true", "1") or settings.LANGFUSE_ENABLED
    
    if not (pub_key and sec_key) and not explicit_flag:
        return False
    
    if not (pub_key and sec_key):
        logger.warning("LANGFUSE_ENABLED is true but LANGFUSE_PUBLIC_KEY/SECRET_KEY not set")
        return False
    
    return True


def observe(name: Optional[str] = None, as_type: Optional[str] = None, **kwargs):
    """
    Fail-safe observation decorator for spans, generations, and traces.
    
    If Langfuse is configured, wraps function execution with Langfuse telemetry.
    If unconfigured or disabled, returns a transparent no-op wrapper with 0 overhead.
    """
    def decorator(fn: Callable) -> Callable:
        if is_langfuse_configured():
            try:
                import langfuse
                dec_kwargs: Dict[str, Any] = {}
                if name:
                    dec_kwargs["name"] = name
                if as_type:
                    dec_kwargs["as_type"] = as_type
                dec_kwargs.update(kwargs)
                return langfuse.observe(**dec_kwargs)(fn)
            except Exception as e:
                logger.warning(f"Failed to attach Langfuse observer to {name or fn.__name__}: {e}")
                return fn

        # Transparent zero-cost fallback
        @functools.wraps(fn)
        def sync_wrapper(*args, **fn_kwargs):
            return fn(*args, **fn_kwargs)

        return sync_wrapper

    return decorator


def flush_langfuse():
    """Flush pending telemetry events to Langfuse if configured."""
    if is_langfuse_configured():
        try:
            import langfuse
            client = langfuse.get_client()
            client.flush()
        except Exception as e:
            logger.debug(f"Langfuse flush error: {e}")
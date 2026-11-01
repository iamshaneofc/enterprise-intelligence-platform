"""Rate limiting middleware for API protection."""
import time
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from backend.app.core.config import settings
from backend.app.core.logging import logger


class InMemoryRateLimiter:
    """Simple in-memory rate limiter using sliding window."""
    
    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)
    
    def is_allowed(self, key: str, limit: int, window_seconds: int) -> Tuple[bool, int]:
        """
        Check if request is allowed.
        
        Returns:
            (allowed, remaining_requests)
        """
        now = time.time()
        window_start = now - window_seconds
        
        # Clean old entries
        self.requests[key] = [ts for ts in self.requests[key] if ts > window_start]
        
        current_count = len(self.requests[key])
        if current_count >= limit:
            return False, 0
        
        self.requests[key].append(now)
        return True, limit - current_count - 1
    
    def get_reset_time(self, key: str, window_seconds: int) -> int:
        """Get seconds until rate limit resets."""
        if not self.requests[key]:
            return 0
        oldest = min(self.requests[key])
        return max(0, int(oldest + window_seconds - time.time()))


# Global rate limiter instances
auth_rate_limiter = InMemoryRateLimiter()
upload_rate_limiter = InMemoryRateLimiter()
general_rate_limiter = InMemoryRateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limits on sensitive endpoints."""
    
    def __init__(self, app):
        super().__init__(app)
        # Rate limit configuration
        self.auth_limit = getattr(settings, 'RATE_LIMIT_AUTH', 10)  # 10 requests
        self.auth_window = getattr(settings, 'RATE_LIMIT_AUTH_WINDOW', 60)  # per minute
        self.upload_limit = getattr(settings, 'RATE_LIMIT_UPLOAD', 5)  # 5 uploads
        self.upload_window = getattr(settings, 'RATE_LIMIT_UPLOAD_WINDOW', 300)  # per 5 minutes
        self.general_limit = getattr(settings, 'RATE_LIMIT_GENERAL', 100)  # 100 requests
        self.general_window = getattr(settings, 'RATE_LIMIT_GENERAL_WINDOW', 60)  # per minute
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method
        client_ip = self._get_client_ip(request)
        
        # Determine rate limit based on endpoint
        if path.startswith("/api/v1/auth/") and method == "POST":
            # Auth endpoints (login, register)
            limiter = auth_rate_limiter
            limit = self.auth_limit
            window = self.auth_window
            key = f"auth:{client_ip}"
        elif path.startswith("/api/v1/workspaces/") and "/documents/upload" in path and method == "POST":
            # Document upload
            limiter = upload_rate_limiter
            limit = self.upload_limit
            window = self.upload_window
            key = f"upload:{client_ip}"
        else:
            # General API
            limiter = general_rate_limiter
            limit = self.general_limit
            window = self.general_window
            key = f"general:{client_ip}"
        
        allowed, remaining = limiter.is_allowed(key, limit, window)
        
        if not allowed:
            reset_time = limiter.get_reset_time(key, window)
            logger.warning(f"Rate limit exceeded for {key} on {path}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time),
                }
            )
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
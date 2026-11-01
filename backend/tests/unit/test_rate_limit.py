"""Tests for rate limiting middleware."""
import pytest
from fastapi.testclient import TestClient
from backend.app.core.rate_limit import InMemoryRateLimiter


def test_rate_limiter_allows_within_limit():
    """Test that rate limiter allows requests within limit."""
    limiter = InMemoryRateLimiter()
    key = "test_key"
    limit = 5
    window = 60
    
    for i in range(limit):
        allowed, remaining = limiter.is_allowed(key, limit, window)
        assert allowed is True
        assert remaining == limit - i - 1
    
    # Next request should be denied
    allowed, remaining = limiter.is_allowed(key, limit, window)
    assert allowed is False
    assert remaining == 0


def test_rate_limiter_resets_after_window():
    """Test that rate limiter resets after time window."""
    import time
    limiter = InMemoryRateLimiter()
    key = "test_key_reset"
    limit = 2
    window = 1  # 1 second window
    
    # Use up the limit
    assert limiter.is_allowed(key, limit, window)[0] is True
    assert limiter.is_allowed(key, limit, window)[0] is True
    assert limiter.is_allowed(key, limit, window)[0] is False
    
    # Wait for window to pass
    time.sleep(1.1)
    
    # Should be allowed again
    assert limiter.is_allowed(key, limit, window)[0] is True


def test_rate_limiter_different_keys_independent():
    """Test that different keys have independent limits."""
    limiter = InMemoryRateLimiter()
    limit = 2
    window = 60
    
    # Exhaust limit for key1
    assert limiter.is_allowed("key1", limit, window)[0] is True
    assert limiter.is_allowed("key1", limit, window)[0] is True
    assert limiter.is_allowed("key1", limit, window)[0] is False
    
    # key2 should still be allowed
    assert limiter.is_allowed("key2", limit, window)[0] is True
    assert limiter.is_allowed("key2", limit, window)[0] is True


def test_get_reset_time():
    """Test get_reset_time returns correct value."""
    import time
    limiter = InMemoryRateLimiter()
    key = "test_reset"
    limit = 2
    window = 10  # 10 seconds
    
    # Make one request
    limiter.is_allowed(key, limit, window)
    
    reset_time = limiter.get_reset_time(key, window)
    assert 9 <= reset_time <= 10
    
    # After window passes
    time.sleep(11)
    reset_time = limiter.get_reset_time(key, window)
    assert reset_time == 0


# Integration test for rate limiting middleware
def test_rate_limit_middleware_on_auth(client: TestClient):
    """Test that rate limiting works on auth endpoints."""
    # This test is run with increased limits in conftest.py
    # Just verify the middleware doesn't break normal requests
    response = client.post("/api/v1/auth/register", json={
        "email": "ratelimit_test@test.com",
        "password": "Password123!",
        "full_name": "Rate Limit Test",
    })
    assert response.status_code == 201
    
    # Check rate limit headers present
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers


def test_rate_limit_middleware_on_upload(client: TestClient, auth_headers: dict):
    """Test that rate limiting works on upload endpoints."""
    ws_resp = client.get("/api/v1/workspaces", headers=auth_headers)
    workspace_id = ws_resp.json()[0]["id"]
    
    # Upload a small file
    import io
    content = b"Test document for rate limiting"
    files = {"file": ("test.txt", io.BytesIO(content), "text/plain")}
    
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/documents/upload",
        headers=auth_headers,
        files=files,
    )
    assert response.status_code == 201
    
    # Check rate limit headers present
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
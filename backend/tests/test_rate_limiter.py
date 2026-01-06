"""
Tests for rate limiting functionality.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from app.utils.rate_limiter import (
    RateLimitConfig,
    RateLimitEntry,
    InMemoryRateLimiter,
    RateLimiter,
    get_rate_limiter,
    check_rate_limit,
    load_rate_limits_from_config,
    apply_rate_limit_config,
)


class TestRateLimitConfig:
    """Tests for RateLimitConfig dataclass."""

    def test_default_values(self):
        config = RateLimitConfig(requests=10, window_seconds=60)
        assert config.requests == 10
        assert config.window_seconds == 60


class TestRateLimitEntry:
    """Tests for RateLimitEntry dataclass."""

    def test_default_values(self):
        entry = RateLimitEntry()
        assert entry.requests == 0
        assert entry.concurrent == 0
        assert entry.window_start > 0


class TestInMemoryRateLimiter:
    """Tests for InMemoryRateLimiter."""

    @pytest.fixture
    def limiter(self):
        return InMemoryRateLimiter()

    @pytest.fixture
    def config(self):
        return RateLimitConfig(requests=3, window_seconds=60)

    @pytest.mark.asyncio
    async def test_first_request_allowed(self, limiter, config):
        allowed, remaining, retry = await limiter.check_rate_limit("client1", config)
        assert allowed is True
        assert remaining == 2
        assert retry == 0

    @pytest.mark.asyncio
    async def test_requests_within_limit(self, limiter, config):
        for i in range(3):
            allowed, remaining, retry = await limiter.check_rate_limit(
                "client1", config
            )
            assert allowed is True
            assert remaining == 2 - i

    @pytest.mark.asyncio
    async def test_request_exceeds_limit(self, limiter, config):
        # Make 3 requests (should all succeed)
        for _ in range(3):
            await limiter.check_rate_limit("client1", config)

        # 4th request should fail
        allowed, remaining, retry = await limiter.check_rate_limit("client1", config)
        assert allowed is False
        assert remaining == 0
        assert retry > 0

    @pytest.mark.asyncio
    async def test_different_clients_independent(self, limiter, config):
        # Client 1 makes 3 requests
        for _ in range(3):
            await limiter.check_rate_limit("client1", config)

        # Client 2 should still be able to make requests
        allowed, remaining, retry = await limiter.check_rate_limit("client2", config)
        assert allowed is True
        assert remaining == 2

    @pytest.mark.asyncio
    async def test_concurrent_limit(self, limiter):
        config = RateLimitConfig(requests=2, window_seconds=60)

        # First 2 concurrent requests should succeed
        for i in range(2):
            allowed, remaining, retry = await limiter.check_rate_limit(
                "client1", config, is_concurrent=True
            )
            assert allowed is True
            assert remaining == 1 - i

        # 3rd concurrent request should fail
        allowed, remaining, retry = await limiter.check_rate_limit(
            "client1", config, is_concurrent=True
        )
        assert allowed is False
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_release_concurrent(self, limiter):
        config = RateLimitConfig(requests=2, window_seconds=60)

        # Use 2 concurrent slots
        await limiter.check_rate_limit("client1", config, is_concurrent=True)
        await limiter.check_rate_limit("client1", config, is_concurrent=True)

        # Try to use a 3rd slot (should fail)
        allowed, _, _ = await limiter.check_rate_limit(
            "client1", config, is_concurrent=True
        )
        assert allowed is False

        # Release one slot
        await limiter.release_concurrent("client1")

        # Now should be able to use it again
        allowed, _, _ = await limiter.check_rate_limit(
            "client1", config, is_concurrent=True
        )
        assert allowed is True

    def test_get_client_id_from_forwarded_header(self):
        limiter = InMemoryRateLimiter()
        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1"}
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        client_id = limiter.get_client_id(mock_request)
        assert client_id == "192.168.1.1"

    def test_get_client_id_without_forwarded_header(self):
        limiter = InMemoryRateLimiter()
        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "192.168.1.100"

        client_id = limiter.get_client_id(mock_request)
        assert client_id == "192.168.1.100"


class TestRateLimiter:
    """Tests for RateLimiter manager class."""

    @pytest.fixture
    def storage(self):
        return InMemoryRateLimiter()

    @pytest.fixture
    def limiter(self, storage):
        return RateLimiter(storage=storage)

    def test_default_limits_configured(self, limiter):
        assert limiter.get_config("chat_message").requests == 10
        assert limiter.get_config("chat_stream").requests == 5
        assert limiter.get_config("config_update").requests == 5
        assert limiter.get_config("default").requests == 30

    def test_configure_custom_limits(self, limiter):
        limiter.configure({"custom_endpoint": {"requests": 100, "window_seconds": 120}})
        config = limiter.get_config("custom_endpoint")
        assert config.requests == 100
        assert config.window_seconds == 120

    def test_get_config_unknown_endpoint_uses_default(self, limiter):
        config = limiter.get_config("unknown_endpoint")
        assert config.requests == 30  # default value

    def test_is_enabled_by_default(self, limiter):
        assert limiter.is_enabled() is True

    def test_set_enabled(self, limiter):
        limiter.set_enabled(False)
        assert limiter.is_enabled() is False
        limiter.set_enabled(True)
        assert limiter.is_enabled() is True


class TestConfigLoading:
    """Tests for configuration loading functions."""

    def test_load_rate_limits_from_config_full(self):
        config = {
            "rate_limiting": {
                "enabled": True,
                "endpoints": {"chat_message": {"requests": 15, "window_seconds": 120}},
            }
        }
        result = load_rate_limits_from_config(config)
        assert result["enabled"] is True
        assert result["endpoints"]["chat_message"]["requests"] == 15
        assert result["endpoints"]["chat_message"]["window_seconds"] == 120

    def test_load_rate_limits_from_config_empty(self):
        config = {}
        result = load_rate_limits_from_config(config)
        assert result["enabled"] is True
        assert result["endpoints"] == {}

    def test_load_rate_limits_from_config_disabled(self):
        config = {"rate_limiting": {"enabled": False, "endpoints": {}}}
        result = load_rate_limits_from_config(config)
        assert result["enabled"] is False

    def test_apply_rate_limit_config(self):
        limiter = get_rate_limiter()
        config = {
            "enabled": False,
            "endpoints": {"test_endpoint": {"requests": 50, "window_seconds": 30}},
        }
        apply_rate_limit_config(config)
        assert limiter.is_enabled() is False
        assert limiter.get_config("test_endpoint").requests == 50


class TestIntegration:
    """Integration tests for rate limiting."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset the global rate limiter singleton before each test."""
        global _rate_limiter
        _rate_limiter = None
        yield
        _rate_limiter = None

    @pytest.mark.asyncio
    async def test_rate_limit_middleware_flow(self):
        """Test the complete flow of rate limiting."""
        limiter = RateLimiter()
        limiter.set_enabled(True)

        # Create a mock request
        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "test-client"

        # First request should succeed
        is_allowed, response = await limiter.check_rate_limit(
            mock_request, endpoint_key="chat_message"
        )
        assert is_allowed is True
        assert response is None

    @pytest.mark.asyncio
    async def test_rate_limit_returns_429_response(self):
        """Test that rate limit exceeded returns 429 response."""
        limiter = RateLimiter()
        limiter.configure({"test_endpoint": {"requests": 1, "window_seconds": 60}})

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "test-client-2"

        # First request should succeed
        is_allowed, response = await limiter.check_rate_limit(
            mock_request, endpoint_key="test_endpoint"
        )
        assert is_allowed is True

        # Second request should fail with 429
        is_allowed, response = await limiter.check_rate_limit(
            mock_request, endpoint_key="test_endpoint"
        )
        assert is_allowed is False
        assert response is not None
        assert response.status_code == 429
        assert "Retry-After" in response.headers

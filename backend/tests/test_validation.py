"""
Tests for API key validation functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from app.config.validate import (
    validate_api_key,
    validate_anthropic,
    validate_openai,
    validate_openrouter,
    validate_tavily,
    ValidationCache,
    clear_validation_cache,
    get_validation_cache_stats,
)


class TestValidationCache:
    """Test the ValidationCache class."""

    def setup_method(self):
        """Create a fresh cache for each test."""
        self.cache = ValidationCache(ttl_seconds=60)

    def test_set_and_get(self):
        """Test basic set and get operations."""
        result = {"valid": True, "message": "Test"}
        self.cache.set("anthropic", "test-key-123", result)

        cached = self.cache.get("anthropic", "test-key-123")
        assert cached == result

    def test_cache_key_generation(self):
        """Test that different keys generate different cache entries."""
        result1 = {"valid": True, "message": "Key 1"}
        result2 = {"valid": False, "message": "Key 2"}

        self.cache.set("anthropic", "key-1", result1)
        self.cache.set("anthropic", "key-2", result2)

        # Both should be retrievable
        assert self.cache.get("anthropic", "key-1") == result1
        assert self.cache.get("anthropic", "key-2") == result2

    def test_ttl_expiration(self):
        """Test that cache entries expire after TTL."""
        cache = ValidationCache(ttl_seconds=1)  # 1 second TTL
        result = {"valid": True, "message": "Test"}

        cache.set("anthropic", "test-key", result)

        # Should be available immediately
        assert cache.get("anthropic", "test-key") == result

        # Wait for expiration
        import time

        time.sleep(1.1)

        # Should be expired
        assert cache.get("anthropic", "test-key") is None

    def test_clear_cache(self):
        """Test clearing the cache."""
        self.cache.set("anthropic", "key1", {"valid": True})
        self.cache.set("openai", "key2", {"valid": False})

        assert self.cache.get("anthropic", "key1") is not None
        assert self.cache.get("openai", "key2") is not None

        self.cache.clear()

        assert self.cache.get("anthropic", "key1") is None
        assert self.cache.get("openai", "key2") is None

    def test_get_stats(self):
        """Test getting cache statistics."""
        self.cache.set("anthropic", "key1", {"valid": True})
        self.cache.set("openai", "key2", {"valid": False})

        stats = self.cache.get_stats()
        assert stats["cache_size"] == 2
        assert stats["ttl_seconds"] == 60


class TestValidateAnthropic:
    """Test Anthropic API key validation."""

    @pytest.mark.asyncio
    async def test_valid_api_key(self):
        """Test validation with a valid API key."""
        with patch("anthropic.Anthropic") as mock_client:
            mock_client.return_value.messages.create = AsyncMock()

            result = await validate_anthropic("sk-ant-valid-key")

            assert result["valid"] is True
            assert result["provider"] == "anthropic"

    @pytest.mark.asyncio
    async def test_invalid_api_key(self):
        """Test validation with an invalid API key."""
        import anthropic

        with patch("anthropic.Anthropic") as mock_client:
            mock_client.return_value.messages.create = AsyncMock(
                side_effect=anthropic.AuthenticationError("Invalid API key")
            )

            result = await validate_anthropic("sk-ant-invalid-key")

            assert result["valid"] is False
            assert result["provider"] == "anthropic"
            assert result["error_type"] == "authentication"

    @pytest.mark.asyncio
    async def test_empty_api_key(self):
        """Test validation with empty API key."""
        result = await validate_anthropic("")

        assert result["valid"] is False
        assert "too short" in result["message"].lower()


class TestValidateOpenAI:
    """Test OpenAI API key validation."""

    @pytest.mark.asyncio
    async def test_valid_api_key(self):
        """Test validation with a valid API key."""
        with patch("openai.AsyncOpenAI") as mock_client:
            mock_client.return_value.models.list = AsyncMock()

            result = await validate_openai("sk-valid-key")

            assert result["valid"] is True
            assert result["provider"] == "openai"

    @pytest.mark.asyncio
    async def test_invalid_api_key(self):
        """Test validation with an invalid API key."""
        import openai

        with patch("openai.AsyncOpenAI") as mock_client:
            mock_client.return_value.models.list = AsyncMock(
                side_effect=openai.AuthenticationError("Invalid API key")
            )

            result = await validate_openai("sk-invalid-key")

            assert result["valid"] is False
            assert result["provider"] == "openai"
            assert result["error_type"] == "authentication"


class TestValidateTavily:
    """Test Tavily API key validation."""

    @pytest.mark.asyncio
    async def test_valid_api_key(self):
        """Test validation with a valid API key."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await validate_tavily("tvly-valid-key")

            assert result["valid"] is True
            assert result["provider"] == "tavily"

    @pytest.mark.asyncio
    async def test_invalid_api_key(self):
        """Test validation with an invalid API key."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await validate_tavily("tvly-invalid-key")

            assert result["valid"] is False
            assert result["provider"] == "tavily"
            assert result["error_type"] == "authentication"


class TestMainValidateFunction:
    """Test the main validate_api_key function."""

    @pytest.mark.asyncio
    async def test_unknown_provider(self):
        """Test validation with unknown provider."""
        result = await validate_api_key("unknown_provider", "some-key")

        assert result["valid"] is False
        assert result["error_type"] == "validation"

    @pytest.mark.asyncio
    async def test_short_api_key(self):
        """Test validation with too short API key."""
        result = await validate_api_key("anthropic", "short")

        assert result["valid"] is False
        assert result["error_type"] == "validation"

    @pytest.mark.asyncio
    async def test_caching(self):
        """Test that validation results are cached."""
        # Clear cache first
        clear_validation_cache()

        with patch("anthropic.Anthropic") as mock_client:
            mock_client.return_value.messages.create = AsyncMock()

            # First call - should make API request
            result1 = await validate_api_key("anthropic", "cached-key")

            # Second call - should use cache
            result2 = await validate_api_key("anthropic", "cached-key")

            assert result1 == result2
            # Verify client was only created once (cached)
            assert mock_client.call_count == 1


# Fixtures
@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client."""
    with patch("anthropic.Anthropic") as mock:
        yield mock


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    with patch("openai.AsyncOpenAI") as mock:
        yield mock


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])

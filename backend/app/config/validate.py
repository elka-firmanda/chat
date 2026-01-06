"""
API Key Validation Module

Provides validation functions for all supported providers (Anthropic, OpenAI, OpenRouter, Tavily).
Includes caching with 5-minute TTL to reduce API calls.
"""

import asyncio
import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


# Validation cache with TTL
class ValidationCache:
    """Simple in-memory cache for validation results with TTL."""

    def __init__(self, ttl_seconds: int = 300):  # 5 minutes default TTL
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _get_key(self, provider: str, api_key: str) -> str:
        """Generate cache key from provider and API key."""
        # Hash the API key to avoid storing it in plain text
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        return f"{provider}:{key_hash}"

    def get(self, provider: str, api_key: str) -> Optional[Dict[str, Any]]:
        """Get cached validation result if valid."""
        key = self._get_key(provider, api_key)
        if key in self._cache:
            cached = self._cache[key]
            if datetime.now() < cached["expires_at"]:
                return cached["result"]
            else:
                del self._cache[key]
        return None

    def set(self, provider: str, api_key: str, result: Dict[str, Any]) -> None:
        """Cache validation result with TTL."""
        key = self._get_key(provider, api_key)
        self._cache[key] = {
            "result": result,
            "expires_at": datetime.now() + timedelta(seconds=self.ttl_seconds),
        }

    def clear(self) -> None:
        """Clear all cached results."""
        self._cache.clear()


# Global validation cache instance
validation_cache = ValidationCache(ttl_seconds=300)


# Provider validation functions
async def validate_anthropic(api_key: str) -> Dict[str, Any]:
    """Validate Anthropic API key by making a minimal API call."""
    import anthropic

    try:
        client = anthropic.Anthropic(api_key=api_key, timeout=10)

        # Make a minimal API call using messages API
        # Using a very short max_tokens to minimize cost
        # Run sync SDK call in a thread to avoid blocking
        response = await asyncio.to_thread(
            client.messages.create,
            model="claude-sonnet-4-20250514",
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}],
        )

        logger.info(
            f"Anthropic validation successful for key starting with {api_key[:10]}..."
        )
        return {
            "valid": True,
            "provider": "anthropic",
            "message": "API key is valid",
            "model_used": "claude-sonnet-4-20250514",
        }

    except anthropic.AuthenticationError as e:
        logger.error(f"Anthropic auth error: {e}")
        return {
            "valid": False,
            "provider": "anthropic",
            "message": "Invalid API key or authentication failed",
            "error_type": "authentication",
        }
    except anthropic.BadRequestError as e:
        logger.error(f"Anthropic bad request error: {e}")
        return {
            "valid": False,
            "provider": "anthropic",
            "message": f"Bad request: {str(e)}",
            "error_type": "bad_request",
        }
    except anthropic.APIStatusError as e:
        status_code = e.status_code
        logger.error(f"Anthropic API status error ({status_code}): {e}")
        return {
            "valid": False,
            "provider": "anthropic",
            "message": f"API error (status {status_code}): {str(e)}",
            "error_type": f"http_{status_code}",
        }
    except anthropic.APIConnectionError as e:
        logger.error(f"Anthropic connection error: {e}")
        return {
            "valid": False,
            "provider": "anthropic",
            "message": f"Connection error: {str(e)}",
            "error_type": "connection",
        }
    except anthropic.APIError as e:
        logger.error(f"Anthropic API error: {e}")
        return {
            "valid": False,
            "provider": "anthropic",
            "message": f"API error: {str(e)}",
            "error_type": "api_error",
        }
    except asyncio.TimeoutError:
        logger.error("Anthropic request timed out")
        return {
            "valid": False,
            "provider": "anthropic",
            "message": "Request timed out",
            "error_type": "timeout",
        }
    except Exception as e:
        logger.error(f"Anthropic unexpected error: {type(e).__name__}: {e}")
        return {
            "valid": False,
            "provider": "anthropic",
            "message": f"Unexpected error: {type(e).__name__}: {str(e)}",
            "error_type": "unknown",
        }


async def validate_openai(api_key: str) -> Dict[str, Any]:
    """Validate OpenAI API key by making a minimal API call."""
    from openai import AsyncOpenAI, AuthenticationError as OpenAIAuthError

    try:
        client = AsyncOpenAI(api_key=api_key, timeout=10)

        # Make a minimal API call to list models
        # This is the cheapest way to validate an OpenAI key
        response = await asyncio.wait_for(
            client.models.list(),
            timeout=10,
        )

        return {
            "valid": True,
            "provider": "openai",
            "message": "API key is valid",
            "model": "models.list",
        }

    except OpenAIAuthError as e:
        return {
            "valid": False,
            "provider": "openai",
            "message": "Invalid API key or authentication failed",
            "error_type": "authentication",
        }
    except asyncio.TimeoutError:
        return {
            "valid": False,
            "provider": "openai",
            "message": "Request timed out",
            "error_type": "timeout",
        }
    except Exception as e:
        error_msg = str(e)
        if "authentication" in error_msg.lower() or "401" in error_msg:
            return {
                "valid": False,
                "provider": "openai",
                "message": "Invalid API key or authentication failed",
                "error_type": "authentication",
            }
        elif "rate limit" in error_msg.lower() or "429" in error_msg:
            return {
                "valid": False,
                "provider": "openai",
                "message": "Rate limit exceeded. Please try again later.",
                "error_type": "rate_limit",
            }
        else:
            return {
                "valid": False,
                "provider": "openai",
                "message": f"Validation failed: {error_msg}",
                "error_type": "unknown",
            }


async def validate_openrouter(api_key: str) -> Dict[str, Any]:
    """Validate OpenRouter API key by making a minimal API call."""
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            timeout=10,
            default_headers={
                "HTTP-Referer": "https://github.com/your-org/agentic-chatbot",
                "X-Title": "Agentic Chatbot",
            },
        )

        # Make a minimal API call to list models
        response = await asyncio.wait_for(
            client.models.list(),
            timeout=10,
        )

        return {
            "valid": True,
            "provider": "openrouter",
            "message": "API key is valid",
            "model": "models.list",
        }

    except Exception as e:
        error_msg = str(e)
        if "authentication" in error_msg.lower() or "401" in error_msg:
            return {
                "valid": False,
                "provider": "openrouter",
                "message": "Invalid API key or authentication failed",
                "error_type": "authentication",
            }
        elif "rate limit" in error_msg.lower() or "429" in error_msg:
            return {
                "valid": False,
                "provider": "openrouter",
                "message": "Rate limit exceeded. Please try again later.",
                "error_type": "rate_limit",
            }
        else:
            return {
                "valid": False,
                "provider": "openrouter",
                "message": f"Validation failed: {error_msg}",
                "error_type": "unknown",
            }


async def validate_tavily(api_key: str) -> Dict[str, Any]:
    """Validate Tavily API key by making a minimal API call."""
    try:
        import httpx

        # Tavily API has a simple endpoint to check API key
        # Using search endpoint with minimal query
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "query": "test",
                    "max_results": 1,
                    "api_key": api_key,
                },
            )

        if response.status_code == 200:
            return {
                "valid": True,
                "provider": "tavily",
                "message": "API key is valid",
            }
        elif response.status_code == 401:
            return {
                "valid": False,
                "provider": "tavily",
                "message": "Invalid API key or authentication failed",
                "error_type": "authentication",
            }
        elif response.status_code == 429:
            return {
                "valid": False,
                "provider": "tavily",
                "message": "Rate limit exceeded. Please try again later.",
                "error_type": "rate_limit",
            }
        else:
            return {
                "valid": False,
                "provider": "tavily",
                "message": f"Validation failed with status {response.status_code}",
                "error_type": "unknown",
            }

    except asyncio.TimeoutError:
        return {
            "valid": False,
            "provider": "tavily",
            "message": "Request timed out",
            "error_type": "timeout",
        }
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "unauthorized" in error_msg.lower():
            return {
                "valid": False,
                "provider": "tavily",
                "message": "Invalid API key or authentication failed",
                "error_type": "authentication",
            }
        elif "429" in error_msg or "rate" in error_msg.lower():
            return {
                "valid": False,
                "provider": "tavily",
                "message": "Rate limit exceeded. Please try again later.",
                "error_type": "rate_limit",
            }
        else:
            return {
                "valid": False,
                "provider": "tavily",
                "message": f"Validation failed: {error_msg}",
                "error_type": "unknown",
            }


# Main validation function
async def validate_api_key(provider: str, api_key: str) -> Dict[str, Any]:
    """
    Validate an API key for the specified provider.

    Args:
        provider: Provider name (anthropic, openai, openrouter, tavily)
        api_key: The API key to validate

    Returns:
        Dict with keys: valid (bool), provider (str), message (str), error_type (str, optional)
    """
    # Check cache first
    cached_result = validation_cache.get(provider, api_key)
    if cached_result:
        logger.debug(f"Returning cached validation result for {provider}")
        return cached_result

    # Validate input
    if not api_key or len(api_key) < 5:
        result = {
            "valid": False,
            "provider": provider,
            "message": "API key is too short or empty",
            "error_type": "validation",
        }
        validation_cache.set(provider, api_key, result)
        return result

    # Validate provider name
    provider = provider.lower()
    valid_providers = ["anthropic", "openai", "openrouter", "tavily"]
    if provider not in valid_providers:
        result = {
            "valid": False,
            "provider": provider,
            "message": f"Unknown provider: {provider}. Valid providers: {', '.join(valid_providers)}",
            "error_type": "validation",
        }
        validation_cache.set(provider, api_key, result)
        return result

    # Call appropriate validation function
    if provider == "anthropic":
        result = await validate_anthropic(api_key)
    elif provider == "openai":
        result = await validate_openai(api_key)
    elif provider == "openrouter":
        result = await validate_openrouter(api_key)
    elif provider == "tavily":
        result = await validate_tavily(api_key)
    else:
        result = {
            "valid": False,
            "provider": provider,
            "message": f"Provider {provider} validation not implemented",
            "error_type": "not_implemented",
        }

    # Cache the result
    validation_cache.set(provider, api_key, result)
    logger.debug(f"Cached validation result for {provider}: {result['valid']}")

    return result


def clear_validation_cache() -> None:
    """Clear all cached validation results."""
    validation_cache.clear()
    logger.info("Validation cache cleared")


def get_validation_cache_stats() -> Dict[str, Any]:
    """Get statistics about the validation cache."""
    return {
        "cache_size": len(validation_cache._cache),
        "ttl_seconds": validation_cache.ttl_seconds,
    }

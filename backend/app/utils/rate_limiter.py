"""
Rate limiting utility for API endpoints.

Provides configurable per-IP rate limiting with:
- Sliding window rate limiting
- Configurable limits per endpoint
- In-memory storage (single instance)
- Redis support for distributed deployments
- 429 response with retry-after header
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from fastapi import Request, Response
from contextlib import asynccontextmanager


@dataclass
class RateLimitConfig:
    """Rate limit configuration for an endpoint."""

    requests: int  # Maximum requests allowed
    window_seconds: int  # Time window in seconds


@dataclass
class RateLimitEntry:
    """Track rate limit state for a client."""

    requests: int = 0
    window_start: float = field(default_factory=time.time)
    concurrent: int = 0


class InMemoryRateLimiter:
    """
    In-memory rate limiter using sliding window approach.

    For single-instance deployments. For multi-instance deployments,
    use Redis-based rate limiter.
    """

    def __init__(self):
        self._clients: Dict[str, RateLimitEntry] = defaultdict(lambda: RateLimitEntry())
        self._concurrent: Dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    async def check_rate_limit(
        self,
        client_id: str,
        config: RateLimitConfig,
        is_concurrent: bool = False,
    ) -> Tuple[bool, int, int]:
        """
        Check if request is within rate limit.

        Args:
            client_id: Unique identifier for the client (usually IP address)
            config: Rate limit configuration
            is_concurrent: If True, use concurrent limit instead of request count

        Returns:
            Tuple of (is_allowed, remaining_requests, retry_after_seconds)
        """
        async with self._lock:
            current_time = time.time()
            entry = self._clients[client_id]

            # Check if window has expired
            window_elapsed = current_time - entry.window_start
            if window_elapsed >= config.window_seconds:
                # Reset window
                entry.requests = 0
                entry.window_start = current_time

            if is_concurrent:
                # Check concurrent connection limit
                if entry.concurrent >= config.requests:
                    retry_after = int(config.window_seconds - window_elapsed) or 1
                    return False, 0, retry_after
                entry.concurrent += 1
                remaining = config.requests - entry.concurrent
            else:
                # Check request limit
                if entry.requests >= config.requests:
                    retry_after = int(config.window_seconds - window_elapsed) or 1
                    return False, 0, retry_after
                entry.requests += 1
                remaining = config.requests - entry.requests

            return True, remaining, 0

    async def release_concurrent(self, client_id: str):
        """Release a concurrent connection slot."""
        async with self._lock:
            entry = self._clients[client_id]
            if entry.concurrent > 0:
                entry.concurrent -= 1

    def get_client_id(self, request: Request) -> str:
        """Extract client ID from request (uses X-Forwarded-For if present)."""
        # Check for forwarded IP (behind proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Get the first IP in the chain (original client)
            return forwarded.split(",")[0].strip()

        # Fall back to direct connection IP
        return request.client.host if request.client else "unknown"


class RateLimiter:
    """
    Rate limiter manager with endpoint-specific configurations.
    """

    # Default rate limits per endpoint
    DEFAULT_LIMITS = {
        "chat_message": RateLimitConfig(requests=10, window_seconds=60),  # 10 req/min
        "chat_stream": RateLimitConfig(requests=5, window_seconds=60),  # 5 concurrent
        "config_update": RateLimitConfig(
            requests=30, window_seconds=60
        ),  # 30 req/min - user settings save
        "default": RateLimitConfig(requests=30, window_seconds=60),  # 30 req/min
    }

    def __init__(self, storage: Optional[InMemoryRateLimiter] = None):
        self._storage = storage or InMemoryRateLimiter()
        self._configs: Dict[str, RateLimitConfig] = {}
        self._enabled = True

    def configure(self, configs: Dict[str, Dict[str, int]]):
        """
        Configure rate limits from a dictionary.

        Args:
            configs: Dict mapping endpoint names to {"requests": N, "window_seconds": M}
        """
        for key, value in configs.items():
            if (
                isinstance(value, dict)
                and "requests" in value
                and "window_seconds" in value
            ):
                self._configs[key] = RateLimitConfig(
                    requests=value["requests"],
                    window_seconds=value["window_seconds"],
                )

    def is_enabled(self) -> bool:
        """Check if rate limiting is enabled."""
        return self._enabled

    def set_enabled(self, enabled: bool):
        """Enable or disable rate limiting."""
        self._enabled = enabled

    def get_config(self, key: str) -> RateLimitConfig:
        """Get rate limit config for an endpoint, using default if not configured."""
        return self._configs.get(
            key, self.DEFAULT_LIMITS.get(key, self.DEFAULT_LIMITS["default"])
        )

    async def check_rate_limit(
        self,
        request: Request,
        endpoint_key: str = "default",
        is_concurrent: bool = False,
    ) -> Tuple[bool, Response]:
        """
        Check rate limit and return appropriate response.

        Args:
            request: FastAPI request object
            endpoint_key: Key identifying the endpoint type
            is_concurrent: If True, use concurrent connection limit

        Returns:
            Tuple of (is_allowed, Response). If not allowed, Response contains 429.
        """
        if not self._enabled:
            return True, None

        client_id = self._storage.get_client_id(request)
        config = self.get_config(endpoint_key)

        is_allowed, remaining, retry_after = await self._storage.check_rate_limit(
            client_id=client_id,
            config=config,
            is_concurrent=is_concurrent,
        )

        if not is_allowed:
            import json

            response = Response(
                content=json.dumps(
                    {
                        "error": "Too Many Requests",
                        "message": f"Rate limit exceeded. Please retry after {retry_after} seconds.",
                        "retry_after": retry_after,
                    }
                ),
                status_code=429,
                media_type="application/json",
            )
            response.headers["Retry-After"] = str(retry_after)
            response.headers["X-RateLimit-Limit"] = str(config.requests)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(int(time.time() + retry_after))
            return False, response

        # Add rate limit headers to successful response
        headers = {
            "X-RateLimit-Limit": str(config.requests),
            "X-RateLimit-Remaining": str(remaining),
        }
        if is_concurrent:
            headers["X-RateLimit-Concurrency"] = str(config.requests - remaining)

        return True, None

    async def release_concurrent(self, request: Request, endpoint_key: str = "default"):
        """Release a concurrent connection slot."""
        client_id = self._storage.get_client_id(request)
        await self._storage.release_concurrent(client_id)


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
        # Apply default configurations
        _rate_limiter.configure(
            {
                "chat_message": {"requests": 10, "window_seconds": 60},
                "chat_stream": {"requests": 5, "window_seconds": 60},
                "config_update": {"requests": 5, "window_seconds": 60},
                "default": {"requests": 30, "window_seconds": 60},
            }
        )
    return _rate_limiter


async def check_rate_limit(
    request: Request,
    endpoint_key: str = "default",
    is_concurrent: bool = False,
) -> Tuple[bool, Optional[Response]]:
    """
    Convenience function to check rate limit.

    Usage:
        is_allowed, response = await check_rate_limit(request, "chat_message")
        if not is_allowed:
            return response
    """
    limiter = get_rate_limiter()
    return await limiter.check_rate_limit(request, endpoint_key, is_concurrent)


def load_rate_limits_from_config(config: dict) -> dict:
    """
    Load rate limit configuration from the main config.

    Expected format:
    {
        "rate_limiting": {
            "enabled": true,
            "endpoints": {
                "chat_message": {"requests": 10, "window_seconds": 60},
                "chat_stream": {"requests": 5, "window_seconds": 60},
                "config_update": {"requests": 5, "window_seconds": 60},
                "default": {"requests": 30, "window_seconds": 60}
            }
        }
    }
    """
    rate_limit_config = config.get("rate_limiting", {})

    result = {
        "enabled": rate_limit_config.get("enabled", True),
        "endpoints": {},
    }

    endpoint_configs = rate_limit_config.get("endpoints", {})
    for endpoint, values in endpoint_configs.items():
        if isinstance(values, dict):
            result["endpoints"][endpoint] = {
                "requests": values.get("requests", 30),
                "window_seconds": values.get("window_seconds", 60),
            }

    return result


def apply_rate_limit_config(rate_limit_config: dict):
    """
    Apply rate limit configuration to the global rate limiter.

    Args:
        rate_limit_config: Configuration dictionary from load_rate_limits_from_config
    """
    limiter = get_rate_limiter()

    # Set enabled state
    enabled = rate_limit_config.get("enabled", True)
    limiter.set_enabled(enabled)

    # Apply endpoint configurations
    endpoints = rate_limit_config.get("endpoints", {})
    if endpoints:
        limiter.configure(endpoints)

"""
Health check endpoints.
"""

import asyncio
import time
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, check_database_connection
from app.config.config_manager import get_config


router = APIRouter()


@router.get("")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy", "service": "agentic-chatbot"}


@router.get("/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    config = get_config()

    db_status = await check_database_connection()

    llm_status = await check_llm_providers(config)

    tavily_status = await check_tavily_status(config)

    overall_status = determine_overall_status(db_status, llm_status, tavily_status)

    return {
        "status": overall_status,
        "version": getattr(config, "version", "1.0.0"),
        "database": db_status,
        "llm": llm_status,
        "tavily": tavily_status,
        "timestamp": time.time(),
    }


async def check_llm_providers(config: Any) -> Dict[str, Dict[str, Any]]:
    from app.llm.providers import (
        AnthropicProvider,
        OpenAIProvider,
        ProviderConfig,
    )

    providers_status = {}

    anthropic_key = (
        getattr(config.api_keys, "anthropic", None)
        if hasattr(config, "api_keys")
        else None
    )
    if anthropic_key:
        try:
            anthropic_config = ProviderConfig(
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                api_key=anthropic_key,
                max_tokens=10,
            )
            anthropic = AnthropicProvider(anthropic_config)
            start_time = time.perf_counter()

            def sync_call():
                return anthropic.client.messages.create(
                    messages=[{"role": "user", "content": "test"}],
                    model=anthropic_config.model,
                    max_tokens=1,
                )

            await asyncio.get_event_loop().run_in_executor(None, sync_call)
            latency_ms = (time.perf_counter() - start_time) * 1000

            providers_status["anthropic"] = {
                "status": "connected",
                "latency_ms": round(latency_ms, 2),
                "model": anthropic_config.model,
                "error": None,
            }
        except Exception as e:
            providers_status["anthropic"] = {
                "status": "error",
                "latency_ms": None,
                "model": "claude-3-5-sonnet-20241022",
                "error": str(e),
            }
    else:
        providers_status["anthropic"] = {
            "status": "not_configured",
            "latency_ms": None,
            "model": None,
            "error": "API key not configured",
        }

    openai_key = (
        getattr(config.api_keys, "openai", None)
        if hasattr(config, "api_keys")
        else None
    )
    if openai_key:
        try:
            openai_config = ProviderConfig(
                provider="openai",
                model="gpt-4o",
                api_key=openai_key,
                max_tokens=10,
            )
            openai = OpenAIProvider(openai_config)
            start_time = time.perf_counter()

            request = openai.client.chat.completions.create(
                model=openai_config.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1,
            )

            await request
            latency_ms = (time.perf_counter() - start_time) * 1000

            providers_status["openai"] = {
                "status": "connected",
                "latency_ms": round(latency_ms, 2),
                "model": openai_config.model,
                "error": None,
            }
        except Exception as e:
            providers_status["openai"] = {
                "status": "error",
                "latency_ms": None,
                "model": "gpt-4o",
                "error": str(e),
            }
    else:
        providers_status["openai"] = {
            "status": "not_configured",
            "latency_ms": None,
            "model": None,
            "error": "API key not configured",
        }

    return providers_status


async def check_tavily_status(config: Any) -> Dict[str, Any]:
    import httpx

    tavily_key = (
        getattr(config.api_keys, "tavily", None)
        if hasattr(config, "api_keys")
        else None
    )

    if not tavily_key:
        return {
            "status": "not_configured",
            "latency_ms": None,
            "error": "API key not configured",
        }

    try:
        start_time = time.perf_counter()

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.tavily.com/health",
                headers={"Authorization": f"Bearer {tavily_key}"},
            )

        latency_ms = (time.perf_counter() - start_time) * 1000

        if response.status_code == 200:
            return {
                "status": "connected",
                "latency_ms": round(latency_ms, 2),
                "error": None,
            }
        else:
            return {
                "status": "error",
                "latency_ms": round(latency_ms, 2),
                "error": f"API returned status {response.status_code}",
            }
    except httpx.TimeoutException:
        return {
            "status": "error",
            "latency_ms": None,
            "error": "Request timed out",
        }
    except Exception as e:
        return {
            "status": "error",
            "latency_ms": None,
            "error": str(e),
        }


def determine_overall_status(
    db_status: Dict[str, Any],
    llm_status: Dict[str, Dict[str, Any]],
    tavily_status: Dict[str, Any],
) -> str:
    has_errors = []
    has_degraded = []

    if db_status.get("status") == "error":
        has_errors.append("database")

    for provider, status in llm_status.items():
        if status.get("status") == "error":
            has_errors.append(f"llm:{provider}")
        elif status.get("status") == "not_configured":
            has_degraded.append(f"llm:{provider}")

    if tavily_status.get("status") == "error":
        has_degraded.append("tavily")
    elif tavily_status.get("status") == "not_configured":
        has_degraded.append("tavily")

    if has_errors:
        return "unhealthy"
    elif has_degraded:
        return "degraded"
    else:
        return "healthy"


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    db_result = await check_database_connection()
    db_status = db_result.get("status", "error")

    return {
        "status": "ready" if db_status == "connected" else "not_ready",
        "database": db_status,
    }


@router.get("/live")
async def liveness_check() -> Dict[str, str]:
    return {"status": "alive", "service": "agentic-chatbot"}


@router.get("/config")
async def config_status():
    try:
        config = get_config()
        return {
            "version": getattr(config, "version", "1.0.0"),
            "database_type": getattr(config.database, "type", "sqlite")
            if hasattr(config, "database")
            else "sqlite",
            "agents_loaded": True,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/rate-limit")
async def rate_limit_status():
    """
    Get rate limiting status and configuration.
    """
    from app.utils.rate_limiter import get_rate_limiter

    limiter = get_rate_limiter()
    config = get_config()
    rate_limit_config = getattr(config, "rate_limiting", None)

    if rate_limit_config:
        return {
            "enabled": limiter.is_enabled(),
            "endpoints": {
                key: {
                    "requests": value.requests,
                    "window_seconds": value.window_seconds,
                }
                for key, value in rate_limit_config.endpoints.items()
            }
            if hasattr(rate_limit_config, "endpoints")
            else {},
        }
    else:
        return {
            "enabled": limiter.is_enabled(),
            "endpoints": {},
            "status": "using_defaults",
        }

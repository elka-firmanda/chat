"""
LLM Model Listing - Fetch available models from each LLM provider API.
"""

import logging
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# Anthropic doesn't expose a models list API endpoint
ANTHROPIC_MODELS = [
    {"value": "claude-sonnet-4-20250514", "label": "Claude 4 Sonnet (Latest)"},
    {"value": "claude-opus-4-20250514", "label": "Claude 4 Opus"},
    {"value": "claude-3-5-sonnet-20241022", "label": "Claude 3.5 Sonnet"},
    {"value": "claude-3-5-haiku-20241022", "label": "Claude 3.5 Haiku"},
    {"value": "claude-3-5-sonnet-20240620", "label": "Claude 3.5 Sonnet (June 2024)"},
    {"value": "claude-3-opus-20240229", "label": "Claude 3 Opus"},
    {"value": "claude-3-sonnet-20240229", "label": "Claude 3 Sonnet"},
    {"value": "claude-3-haiku-20240307", "label": "Claude 3 Haiku"},
]


async def list_anthropic_models(api_key: str) -> List[Dict[str, str]]:
    return ANTHROPIC_MODELS.copy()


async def list_openai_models(api_key: str) -> List[Dict[str, str]]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"OpenAI models API error: {e.response.status_code} - {e.response.text}"
            )
            if e.response.status_code == 401:
                raise ValueError(
                    "Invalid OpenAI API key. Please check your API key in Settings."
                )
            raise ValueError(
                f"Failed to fetch OpenAI models: HTTP {e.response.status_code}"
            )
        except httpx.RequestError as e:
            logger.error(f"OpenAI models API request error: {e}")
            raise ValueError(f"Failed to connect to OpenAI models API: {str(e)}")

        data = response.json()

        chat_model_prefixes = ("gpt-4", "gpt-3.5", "o1", "o3")
        excluded_patterns = (
            "instruct",
            "0301",
            "0314",
            "vision",
            "audio",
            "realtime",
            "embedding",
        )

        models = []
        seen_models = set()

        for model in data.get("data", []):
            model_id = model.get("id", "")

            if not model_id.startswith(chat_model_prefixes):
                continue
            if any(pattern in model_id.lower() for pattern in excluded_patterns):
                continue
            if model_id in seen_models:
                continue

            seen_models.add(model_id)

            label = model_id
            if "gpt-4o" in model_id:
                label = f"GPT-4o ({model_id})" if model_id != "gpt-4o" else "GPT-4o"
            elif "gpt-4-turbo" in model_id:
                label = (
                    f"GPT-4 Turbo ({model_id})"
                    if model_id != "gpt-4-turbo"
                    else "GPT-4 Turbo"
                )
            elif "gpt-4" in model_id:
                label = f"GPT-4 ({model_id})" if model_id != "gpt-4" else "GPT-4"
            elif "gpt-3.5-turbo" in model_id:
                label = (
                    f"GPT-3.5 Turbo ({model_id})"
                    if model_id != "gpt-3.5-turbo"
                    else "GPT-3.5 Turbo"
                )
            elif "o1" in model_id:
                label = f"O1 ({model_id})"
            elif "o3" in model_id:
                label = f"O3 ({model_id})"

            models.append({"value": model_id, "label": label})

        def model_priority(m: Dict[str, str]) -> tuple:
            model_id = m["value"]
            if "o3" in model_id:
                return (0, model_id)
            if "o1" in model_id:
                return (1, model_id)
            if "gpt-4o" in model_id:
                return (2, model_id)
            if "gpt-4-turbo" in model_id:
                return (3, model_id)
            if "gpt-4" in model_id:
                return (4, model_id)
            if "gpt-3.5" in model_id:
                return (5, model_id)
            return (6, model_id)

        models.sort(key=model_priority)
        return models


async def list_openrouter_models(api_key: str) -> List[Dict[str, str]]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        response.raise_for_status()
        data = response.json()

        models = []
        for model in data.get("data", []):
            model_id = model.get("id", "")
            model_name = model.get("name", model_id)

            if ":free" in model_id.lower():
                continue

            models.append(
                {
                    "value": model_id,
                    "label": model_name,
                }
            )

        models.sort(key=lambda m: m["label"].lower())
        return models


async def list_models_for_provider(
    provider: str,
    api_key: Optional[str] = None,
) -> List[Dict[str, str]]:
    provider = provider.lower()

    if provider == "anthropic":
        return await list_anthropic_models(api_key or "")
    elif provider == "openai":
        if not api_key:
            raise ValueError("OpenAI API key is required to fetch models")
        return await list_openai_models(api_key)
    elif provider == "openrouter":
        if not api_key:
            raise ValueError("OpenRouter API key is required to fetch models")
        return await list_openrouter_models(api_key)
    else:
        raise ValueError(f"Unknown provider: {provider}")

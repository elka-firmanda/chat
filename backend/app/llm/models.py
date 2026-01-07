"""
LLM Model Listing - Fetch available models from each LLM provider API.
"""

import logging
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


async def list_anthropic_models(api_key: str) -> List[Dict[str, str]]:
    print(api_key)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            "https://api.anthropic.com/v1/models",
            headers={"X-Api-Key": api_key, "anthropic-version": "2023-06-01"},
        )
        response.raise_for_status()
        data = response.json()
        models = []
        for model in data.get("data", []):
            model_id = model.get("id", "")
            model_name = model.get("name", model_id)

            models.append(
                {
                    "value": model_id,
                    "label": model_name,
                }
            )

        models.sort(key=lambda m: m["label"].lower())
    return models


async def list_openai_models(api_key: str) -> List[Dict[str, str]]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        response.raise_for_status()
        data = response.json()
        models = []
        for model in data.get("data", []):
            model_id = model.get("id", "")
            model_name = model.get("name", model_id)

            models.append(
                {
                    "value": model_id,
                    "label": model_name,
                }
            )
        # Filter to only include GPT models
        models = [m for m in models if m["value"].startswith("gpt")]
        models.sort(key=lambda m: m["label"].lower())
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
        if not api_key:
            raise ValueError("Anthropic API key is required to fetch models")
        return await list_anthropic_models(api_key)
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

"""
Configuration management endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from app.config.config_manager import config_manager, get_config
from app.config.schema import ConfigUpdate
from app.config.validate import (
    validate_api_key,
    get_validation_cache_stats,
    clear_validation_cache,
)


router = APIRouter()


@router.get("")
async def get_config_settings():
    """
    Get current configuration (with masked API keys).
    """
    try:
        config = get_config()
        masked_config = config_manager.mask_api_keys(config)
        return masked_config
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def update_config(update: ConfigUpdate):
    """
    Update configuration.
    """
    try:
        updated_config = config_manager.update(update)
        masked_config = config_manager.mask_api_keys(updated_config)
        return masked_config
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-api-key")
async def validate_api_key_endpoint(
    provider: str = Query(
        ..., description="Provider name (anthropic, openai, openrouter, tavily)"
    ),
    api_key: str = Query(..., description="API key to validate"),
    bypass_cache: bool = Query(
        False, description="Bypass cache and make fresh validation request"
    ),
):
    """
    Validate an API key by making a test request to the provider.

    Supports all providers: Anthropic, OpenAI, OpenRouter, Tavily.
    Results are cached for 5 minutes to reduce API calls.

    Returns:
        {
            "valid": boolean,
            "provider": string,
            "message": string,
            "error_type": string (optional, only present if valid=false)
        }
    """
    # Clear cache if bypass is requested
    if bypass_cache:
        clear_validation_cache()

    # Validate input
    if not provider or not api_key:
        raise HTTPException(
            status_code=400,
            detail="Both 'provider' and 'api_key' parameters are required",
        )

    # Validate the API key
    result = await validate_api_key(provider, api_key)

    # Return appropriate status code
    if result["valid"]:
        return result
    else:
        # Return 401 for authentication errors, 400 for validation errors
        if result.get("error_type") == "authentication":
            raise HTTPException(status_code=401, detail=result)
        elif result.get("error_type") == "rate_limit":
            raise HTTPException(status_code=429, detail=result)
        else:
            raise HTTPException(status_code=400, detail=result)


@router.get("/profiles")
async def list_profiles():
    """
    List available configuration profiles.
    """
    try:
        config = get_config()
        profiles = config.profiles

        return {
            "profiles": {
                "fast": {
                    "description": "Fast mode using smaller models",
                    "settings": {
                        "master_model": config.profiles.fast.master.get("model", "N/A"),
                        "planner_model": config.profiles.fast.planner.get(
                            "model", "N/A"
                        ),
                    },
                },
                "deep": {
                    "description": "Deep research mode using larger models",
                    "settings": {
                        "master_model": config.profiles.deep.master.get("model", "N/A"),
                        "researcher_urls": config.profiles.deep.researcher.get(
                            "max_urls_to_scrape", "N/A"
                        ),
                    },
                },
            },
            "current_profile": None,  # Could track current profile
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/profiles/{profile_name}")
async def apply_profile(profile_name: str):
    """
    Apply a configuration profile.
    """
    if profile_name not in ["fast", "deep"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown profile: {profile_name}. Available: fast, deep",
        )

    try:
        updated_config = config_manager.apply_profile(profile_name)
        masked_config = config_manager.mask_api_keys(updated_config)
        return {"profile": profile_name, "config": masked_config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/validate")
async def validate_config():
    """
    Validate current configuration.
    """
    is_valid, error = config_manager.validate()

    if is_valid:
        return {"valid": True, "message": "Configuration is valid"}
    else:
        return {"valid": False, "message": error}


@router.get("/validation-cache/stats")
async def get_validation_cache_status():
    """
    Get validation cache statistics.
    """
    return get_validation_cache_stats()


@router.post("/validation-cache/clear")
async def clear_validation_cache_endpoint():
    """
    Clear the validation cache.
    """
    clear_validation_cache()
    return {"message": "Validation cache cleared successfully"}

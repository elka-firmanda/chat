"""
Configuration management endpoints.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config.config_manager import config_manager, get_config
from app.config.schema import ConfigUpdate


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
async def validate_api_key(provider: str, api_key: str):
    """
    Validate an API key by making a test request.
    """
    # This would make an actual API call to validate the key
    # For now, we just check if it's a non-empty string
    if not api_key or len(api_key) < 10:
        return {"valid": False, "message": "API key is too short"}

    # TODO: Implement actual validation for each provider
    return {"valid": True, "provider": provider, "message": "API key appears valid"}


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

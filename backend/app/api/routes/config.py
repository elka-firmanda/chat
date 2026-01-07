"""
Configuration management endpoints.
"""

import asyncio
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.config.config_manager import config_manager, get_config
from app.config.schema import ConfigUpdate
from app.config.validate import (
    validate_api_key,
    get_validation_cache_stats,
    clear_validation_cache,
)
from app.db.session import (
    validate_database_connection,
    switch_database,
    get_database_info,
    update_config_file,
)
from app.db.migration import migrate_sqlite_to_postgresql
from app.llm.models import list_models_for_provider


router = APIRouter()


class DatabaseConfigUpdate(BaseModel):
    """Database configuration update request."""

    type: str
    sqlite_path: str
    postgresql_connection: str
    pool_size: int


class MigrationRequest(BaseModel):
    """Database migration request."""

    sqlite_path: str
    postgresql_connection: str


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
    List available configuration profiles with their settings.
    Returns current_profile to show which profile is actively applied.
    """
    try:
        config = get_config()
        profiles = config.profiles
        current = config.current_profile

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
            "current_profile": current,
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


@router.post("/database/validate")
async def validate_database_endpoint(update: DatabaseConfigUpdate):
    """
    Validate a database configuration without switching.

    Tests the connection and returns success/failure with details.
    """
    is_valid, message = await validate_database_connection(
        db_type=update.type,
        connection_string=(
            update.postgresql_connection
            if update.type == "postgresql"
            else update.sqlite_path
        ),
        pool_size=update.pool_size,
    )

    if is_valid:
        return {
            "valid": True,
            "message": message,
            "database_type": update.type,
        }
    else:
        raise HTTPException(
            status_code=400,
            detail={
                "valid": False,
                "message": message,
                "database_type": update.type,
            },
        )


@router.post("/database/switch")
async def switch_database_endpoint(
    update: DatabaseConfigUpdate,
    background_tasks: BackgroundTasks,
):
    """
    Switch to a different database configuration.

    This will:
    1. Validate the connection
    2. Update config.json
    3. Initialize the new database connection
    4. Create tables if needed

    Warning: This switches the active database. Ensure you have backed up
    your data before switching database types.
    """
    connection_string = (
        update.postgresql_connection
        if update.type == "postgresql"
        else update.sqlite_path
    )

    is_valid, message = await validate_database_connection(
        db_type=update.type,
        connection_string=connection_string,
        pool_size=update.pool_size,
    )

    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail={
                "valid": False,
                "message": message,
            },
        )

    update_config_file(
        db_type=update.type,
        sqlite_path=update.sqlite_path,
        postgresql_connection=update.postgresql_connection,
        pool_size=update.pool_size,
    )

    success, switch_message = await switch_database(
        db_type=update.type,
        connection_string=connection_string,
        pool_size=update.pool_size,
    )

    if success:
        return {
            "valid": True,
            "message": switch_message,
            "database_type": update.type,
            "config_updated": True,
        }
    else:
        raise HTTPException(
            status_code=500,
            detail={
                "valid": False,
                "message": switch_message,
            },
        )


@router.get("/database/info")
async def get_database_info_endpoint():
    """
    Get information about the current database configuration.
    """
    return get_database_info()


@router.get("/models")
async def list_models_endpoint(
    provider: str = Query(
        ..., description="Provider name (anthropic, openai, openrouter)"
    ),
    api_key: Optional[str] = Query(
        None,
        description="API key for the provider (required for anthropic, openai, openrouter)",
    ),
):
    try:
        if not api_key:
            api_key = config_manager.get_api_key(provider)

        if not api_key and provider.lower() in ("anthropic", "openai", "openrouter"):
            raise HTTPException(
                status_code=400,
                detail=f"{provider} API key not configured. Set {provider.upper()}_API_KEY in .env file.",
            )

        models = await list_models_for_provider(provider, api_key)
        return {"provider": provider, "models": models}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch models: {str(e)}")


@router.post("/database/migrate")
async def migrate_database_endpoint(
    request: MigrationRequest, background_tasks: BackgroundTasks
):
    """
    Migrate data from SQLite to PostgreSQL.

    This will:
    1. Read all data from the source SQLite database
    2. Create the schema on the target PostgreSQL database
    3. Copy all data to PostgreSQL

    Note: This is a one-time migration. After migration, update your
    database settings to use PostgreSQL as the active database.
    """
    sqlite_url = f"sqlite+aiosqlite:///{request.sqlite_path}"

    try:
        result = await migrate_sqlite_to_postgresql(
            sqlite_url=sqlite_url,
            postgresql_url=request.postgresql_connection,
        )

        if result["status"] == "completed":
            return {
                "success": True,
                "message": "Migration completed successfully",
                "details": result,
            }
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "message": f"Migration failed: {result.get('error', 'Unknown error')}",
                    "details": result,
                },
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": f"Migration error: {str(e)}",
            },
        )

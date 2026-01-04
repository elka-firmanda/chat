"""
Configuration manager for handling config.json and .env files.
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv

from .schema import Config, ConfigUpdate
from .settings import settings


class ConfigManager:
    """
    Manages application configuration from config.json and .env files.

    Priority order:
    1. config.json (user settings)
    2. .env (API keys, overrides)
    """

    def __init__(self, config_path: str = "config.json", env_path: str = ".env"):
        self.config_path = Path(config_path)
        self.env_path = Path(env_path)
        self._config: Optional[Config] = None
        self._load_env()

    def _load_env(self) -> None:
        """Load environment variables from .env file."""
        if self.env_path.exists():
            load_dotenv(self.env_path)

    def load(self) -> Config:
        """
        Load configuration from config.json.
        Automatically substitutes ${VAR} placeholders with environment variables.
        """
        if self._config is not None:
            return self._config

        if not self.config_path.exists():
            self._create_default_config()

        with open(self.config_path, "r") as f:
            config_data = json.load(f)

        # Substitute environment variables
        config_data = self._substitute_env_vars(config_data)

        # Validate with Pydantic
        self._config = Config(**config_data)
        return self._config

    def _substitute_env_vars(self, obj: Any) -> Any:
        """
        Recursively substitute ${VAR} patterns with environment variables.
        """
        if isinstance(obj, str):
            # Match ${VAR} pattern
            match = re.match(r"^\$\{(.+)\}$", obj)
            if match:
                var_name = match.group(1)
                return os.getenv(var_name, obj)
            return obj
        elif isinstance(obj, dict):
            return {key: self._substitute_env_vars(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_env_vars(item) for item in obj]
        return obj

    def _create_default_config(self) -> None:
        """Create default config.json file."""
        from .schema import (
            GeneralSettings,
            DatabaseSettings,
            AgentsSettings,
            APIKeys,
            Profiles,
        )

        default_config = Config(
            general=GeneralSettings(),
            database=DatabaseSettings(),
            agents=AgentsSettings(),
            api_keys=APIKeys(),
            profiles=Profiles(),
        )

        with open(self.config_path, "w") as f:
            json.dump(default_config.model_dump(), f, indent=2)

    def save(self, config: Config) -> None:
        """
        Save configuration to config.json.
        Keeps ${VAR} placeholders for API keys.
        """
        config_dict = config.model_dump()

        # Replace actual API keys with placeholders
        api_keys = config_dict.get("api_keys", {})
        for key, value in api_keys.items():
            if value and not value.startswith("${"):
                # Keep actual value if not in .env
                pass

        with open(self.config_path, "w") as f:
            json.dump(config_dict, f, indent=2)

        self._config = config

    def update(self, update: ConfigUpdate) -> Config:
        """
        Update configuration with partial changes.
        """
        current = self.load()

        # Apply updates
        if update.general:
            current.general = update.general
        if update.database:
            current.database = update.database
        if update.agents:
            current.agents = update.agents
        if update.api_keys:
            current.api_keys = update.api_keys
        if update.profiles:
            current.profiles = update.profiles

        self.save(current)
        return current

    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate configuration.
        Returns (is_valid, error_message).
        """
        try:
            config = self.load()

            # Validate API keys are present
            if not config.api_keys.anthropic and not config.api_keys.openai:
                return (
                    False,
                    "At least one LLM API key is required (Anthropic or OpenAI)",
                )

            return True, None
        except Exception as e:
            return False, str(e)

    def mask_api_keys(self, config: Config) -> Dict[str, Any]:
        """
        Create a copy of config with API keys masked for UI display.
        """
        config_dict = config.model_dump()

        api_keys = config_dict.get("api_keys", {})
        for key, value in api_keys.items():
            if value and len(value) > 4:
                api_keys[key] = f"***{value[-4:]}"
            else:
                api_keys[key] = "***"

        config_dict["api_keys"] = api_keys
        return config_dict

    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Get API key for a specific provider.
        Checks config first, then environment variables.
        """
        config = self.load()

        # Map provider names to config keys
        key_map = {
            "anthropic": "anthropic_api_key",
            "openai": "openai_api_key",
            "openrouter": "openrouter_api_key",
            "tavily": "tavily_api_key",
        }

        config_key = key_map.get(provider.lower())
        if config_key:
            # Check config first
            api_keys = getattr(config.api_keys, provider.lower(), None)
            if api_keys:
                return api_keys

            # Check environment
            env_key = config_key.upper()
            return os.getenv(env_key)

        return None

    def apply_profile(self, profile_name: str) -> Config:
        """
        Apply a configuration profile (e.g., 'fast', 'deep').
        """
        config = self.load()
        profiles = config.profiles

        if profile_name == "fast":
            profile = profiles.fast
        elif profile_name == "deep":
            profile = profiles.deep
        else:
            return config

        # Apply profile settings
        if hasattr(profile, "master") and config.agents.master:
            for key, value in profile.master.items():
                setattr(config.agents.master, key, value)

        if hasattr(profile, "planner") and config.agents.planner:
            for key, value in profile.planner.items():
                setattr(config.agents.planner, key, value)

        if hasattr(profile, "researcher") and config.agents.researcher:
            for key, value in profile.researcher.items():
                setattr(config.agents.researcher, key, value)

        if hasattr(profile, "tools") and config.agents.tools:
            for key, value in profile.tools.items():
                setattr(config.agents.tools, key, value)

        if hasattr(profile, "database") and config.agents.database:
            for key, value in profile.database.items():
                setattr(config.agents.database, key, value)

        self.save(config)
        return config


# Create global config manager instance
config_manager = ConfigManager()


def get_config() -> Config:
    """Get the current configuration."""
    return config_manager.load()

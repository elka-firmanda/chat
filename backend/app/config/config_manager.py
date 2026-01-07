"""
Configuration manager for handling config.json and .env files.
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, cast
from dotenv import load_dotenv
from functools import lru_cache

from .schema import Config, ConfigUpdate, APIKeys
from .settings import settings


class ConfigManager:
    def __init__(self, config_path: str = "config.json", env_path: str = ".env"):
        self.config_path = Path(config_path)
        self.env_path = Path(env_path)
        self._config: Optional[Config] = None
        self._config_cache: Optional[Config] = None
        self._config_mtime: float = 0
        self._api_keys: Optional[APIKeys] = None
        self._load_env()

    def _load_env(self) -> None:
        """Load environment variables from .env file."""
        env_locations = [
            self.env_path,
            Path(__file__).parent.parent.parent.parent / ".env",  # project root
            Path.cwd() / ".env",
            Path.cwd().parent / ".env",
        ]
        for env_path in env_locations:
            if env_path.exists():
                load_dotenv(env_path)
                return

    def _is_cache_valid(self) -> bool:
        if self._config_cache is None:
            return False
        try:
            current_mtime = self.config_path.stat().st_mtime
            return current_mtime == self._config_mtime
        except (OSError, FileNotFoundError):
            return False

    def load(self) -> Config:
        if self._is_cache_valid():
            return cast(Config, self._config_cache)

        if not self.config_path.exists():
            self._create_default_config()

        with open(self.config_path, "r") as f:
            config_data = json.load(f)

        config_data = self._substitute_env_vars(config_data)

        self._config = Config(**config_data)
        self._config_cache = self._config
        try:
            self._config_mtime = self.config_path.stat().st_mtime
        except OSError:
            pass
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
        from .schema import (
            GeneralSettings,
            DatabaseSettings,
            AgentsSettings,
            Profiles,
        )

        default_config = Config(
            general=GeneralSettings(),
            database=DatabaseSettings(),
            agents=AgentsSettings(),
            profiles=Profiles(),
        )

        with open(self.config_path, "w") as f:
            json.dump(default_config.model_dump(), f, indent=2)

    def save(self, config: Config) -> None:
        config_dict = config.model_dump()

        with open(self.config_path, "w") as f:
            json.dump(config_dict, f, indent=2)

        self._config = config
        self._config_cache = config
        try:
            self._config_mtime = self.config_path.stat().st_mtime
        except OSError:
            pass

    def update(self, update: ConfigUpdate) -> Config:
        current = self.load()

        if update.general:
            current.general = update.general
        if update.database:
            current.database = update.database
        if update.agents:
            current.agents = update.agents
        if update.profiles:
            current.profiles = update.profiles

        self.save(current)
        return current

    def validate(self) -> tuple[bool, Optional[str]]:
        try:
            self.load()

            api_keys = self.get_api_keys()
            if not api_keys.anthropic and not api_keys.openai:
                return (
                    False,
                    "At least one LLM API key is required (Anthropic or OpenAI). Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env",
                )

            return True, None
        except Exception as e:
            return False, str(e)

    def get_api_keys(self) -> APIKeys:
        if self._api_keys is None:
            self._api_keys = APIKeys(
                anthropic=os.getenv("ANTHROPIC_API_KEY"),
                openai=os.getenv("OPENAI_API_KEY"),
                openrouter=os.getenv("OPENROUTER_API_KEY"),
                tavily=os.getenv("TAVILY_API_KEY"),
            )
        return self._api_keys

    def mask_api_keys(self, config: Config) -> Dict[str, Any]:
        config_dict = config.model_dump()

        api_keys = self.get_api_keys()
        masked_keys = {}
        for key in ["anthropic", "openai", "openrouter", "tavily"]:
            value = getattr(api_keys, key)
            if value and len(value) > 4:
                masked_keys[key] = f"***{value[-4:]}"
            elif value:
                masked_keys[key] = "***"
            else:
                masked_keys[key] = None

        config_dict["api_keys"] = masked_keys
        return config_dict

    def get_api_key(self, provider: str) -> Optional[str]:
        env_map = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "tavily": "TAVILY_API_KEY",
        }

        env_key = env_map.get(provider.lower())
        if env_key:
            return os.getenv(env_key)

        return None

    def apply_profile(self, profile_name: str) -> Config:
        """
        Apply a configuration profile (e.g., 'fast', 'deep').
        Updates current_profile to track the active profile.
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

        # Track current profile
        config.current_profile = profile_name

        self.save(config)
        return config


# Create global config manager instance
config_manager = ConfigManager()


def get_config() -> Config:
    """Get the current configuration."""
    return config_manager.load()

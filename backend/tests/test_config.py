"""
Unit tests for configuration management.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.config.settings import Settings, get_settings
from app.config.config_manager import ConfigManager, config_manager
from app.config.schema import AppConfig


class TestSettings:
    """Test the Settings class."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()

        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.debug is False
        assert settings.database_url is None
        assert settings.anthropic_api_key is None

    def test_environment_variable_override(self):
        """Test that environment variables override defaults."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test-key"}):
            settings = Settings()
            assert settings.anthropic_api_key == "sk-test-key"


class TestConfigManager:
    """Test the ConfigManager class."""

    def test_default_manager(self):
        """Test default config manager."""
        manager = ConfigManager()
        assert manager.config_path is None

    @pytest.mark.asyncio
    async def test_load_with_missing_file(self):
        """Test loading config when file is missing."""
        manager = ConfigManager(config_path="/nonexistent/path/config.json")
        config = await manager.load()
        assert config is None

    def test_generate_default_config(self):
        """Test generating default configuration."""
        config = ConfigManager.generate_default_config()
        assert config.version == "1.0"
        assert "general" in config.model_dump()
        assert "database" in config.model_dump()
        assert "agents" in config.model_dump()

    def test_get_agent_config(self):
        """Test getting agent-specific configuration."""
        default_config = ConfigManager.generate_default_config()

        master_config = default_config.agents.get("master")
        assert master_config is not None
        assert master_config.provider == "anthropic"

        researcher_config = default_config.agents.get("researcher")
        assert researcher_config is not None


class TestAppConfig:
    """Test the AppConfig schema."""

    def test_valid_config(self):
        """Test creating a valid configuration."""
        config = AppConfig(
            version="1.0",
            general={
                "timezone": "UTC",
                "theme": "light",
                "example_questions": ["Test question"],
            },
            database={"type": "sqlite", "sqlite_path": "./test.db"},
            agents={
                "master": {
                    "provider": "anthropic",
                    "model": "claude-3-5-sonnet-20241022",
                    "max_tokens": 4096,
                }
            },
        )

        assert config.version == "1.0"
        assert config.database.type == "sqlite"

    def test_nested_agent_config(self):
        """Test nested agent configuration."""
        config = AppConfig(
            version="1.0",
            agents={
                "master": {
                    "provider": "anthropic",
                    "model": "claude-3-5-sonnet-20241022",
                    "max_tokens": 4096,
                },
                "planner": {
                    "provider": "openai",
                    "model": "gpt-4-turbo",
                    "max_tokens": 2048,
                },
            },
        )

        assert config.agents["master"].provider == "anthropic"
        assert config.agents["planner"].provider == "openai"

    def test_api_keys_in_config(self):
        """Test API keys are accessible in configuration."""
        config = AppConfig(
            version="1.0",
            api_keys={
                "anthropic": "${ANTHROPIC_API_KEY}",
                "openai": "${OPENAI_API_KEY}",
            },
        )

        assert config.api_keys["anthropic"] == "${ANTHROPIC_API_KEY}"

    def test_profiles_in_config(self):
        """Test configuration profiles."""
        config = AppConfig(
            version="1.0",
            profiles={
                "fast": {
                    "master": {"model": "gpt-3.5-turbo"},
                    "planner": {"model": "gpt-3.5-turbo"},
                },
                "deep": {
                    "master": {"model": "claude-3-opus-20240229"},
                    "researcher": {"max_urls_to_scrape": 10},
                },
            },
        )

        assert config.profiles["fast"]["master"]["model"] == "gpt-3.5-turbo"
        assert config.profiles["deep"]["researcher"]["max_urls_to_scrape"] == 10


class TestConfigValidation:
    """Test configuration validation."""

    def test_validate_database_config(self):
        """Test validating database configuration."""
        from app.config.schema import DatabaseConfig

        sqlite_config = DatabaseConfig(type="sqlite", sqlite_path="./test.db")
        assert sqlite_config.type == "sqlite"

    def test_validate_agent_config(self):
        """Test validating agent configuration."""
        from app.config.schema import AgentConfig

        agent_config = AgentConfig(
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            temperature=0.7,
        )

        assert agent_config.provider == "anthropic"
        assert agent_config.max_tokens == 4096
        assert agent_config.temperature == 0.7

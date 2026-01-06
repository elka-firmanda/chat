"""
Configuration schema validation with Pydantic.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


# Rate limiting settings
class RateLimitEndpointSettings(BaseModel):
    requests: int = Field(default=30, ge=1, description="Maximum requests allowed")
    window_seconds: int = Field(default=60, ge=1, description="Time window in seconds")


class RateLimitingSettings(BaseModel):
    enabled: bool = Field(default=True, description="Enable rate limiting")
    endpoints: Dict[str, RateLimitEndpointSettings] = Field(
        default_factory=lambda: {
            "chat_message": RateLimitEndpointSettings(requests=10, window_seconds=60),
            "chat_stream": RateLimitEndpointSettings(requests=5, window_seconds=60),
            "config_update": RateLimitEndpointSettings(requests=5, window_seconds=60),
            "default": RateLimitEndpointSettings(requests=30, window_seconds=60),
        },
        description="Rate limit configuration per endpoint",
    )


# General settings
class GeneralSettings(BaseModel):
    timezone: str = "auto"
    theme: str = "light"
    example_questions: List[str] = Field(
        default_factory=lambda: [
            "What are the latest AI breakthroughs?",
            "Analyze my sales data for Q4",
            "How does quantum computing work?",
            "Generate a chart of user growth",
        ]
    )


# Database settings
class DatabaseSettings(BaseModel):
    type: str = "sqlite"
    sqlite_path: str = "./data/chatbot.db"
    postgresql_connection: Optional[str] = None
    pool_size: int = 5


# Agent settings
class AgentSettings(BaseModel):
    provider: str = "anthropic"
    model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 4096
    temperature: float = 0.7
    system_prompt: str = ""
    # Provider-specific settings
    tavily_api_key: Optional[str] = None
    max_urls_to_scrape: int = 5
    scraping_timeout: int = 600
    enabled_tools: List[str] = Field(default_factory=list)
    sandbox_enabled: bool = True
    data_warehouse_schema: str = ""


# Master agent inherits from AgentSettings
class MasterAgentSettings(AgentSettings):
    system_prompt: str = "You are a master orchestrator that coordinates subagents to answer complex questions."


# Planner agent
class PlannerAgentSettings(AgentSettings):
    system_prompt: str = "You create step-by-step execution plans for the master agent."
    max_tokens: int = 2048


# Researcher agent
class ResearcherAgentSettings(AgentSettings):
    provider: str = "openai"
    model: str = "gpt-4-turbo"
    max_tokens: int = 4096
    tavily_api_key: Optional[str] = None
    max_urls_to_scrape: int = 5
    scraping_timeout: int = 600
    system_prompt: str = "You are a research specialist that finds and analyzes information from the web."


# Tools agent
class ToolsAgentSettings(AgentSettings):
    provider: str = "openai"
    model: str = "gpt-4-turbo"
    max_tokens: int = 2048
    enabled_tools: List[str] = Field(
        default_factory=lambda: ["code_executor", "calculator", "chart_generator"]
    )
    sandbox_enabled: bool = True
    system_prompt: str = (
        "You execute code and calculations to help answer user questions."
    )


# Database agent
class DatabaseAgentSettings(AgentSettings):
    provider: str = "anthropic"
    model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 4096
    data_warehouse_schema: str = ""
    system_prompt: str = "You query and analyze data from the data warehouse."


# Agents container
class AgentsSettings(BaseModel):
    master: MasterAgentSettings = Field(default_factory=MasterAgentSettings)
    planner: PlannerAgentSettings = Field(default_factory=PlannerAgentSettings)
    researcher: ResearcherAgentSettings = Field(default_factory=ResearcherAgentSettings)
    tools: ToolsAgentSettings = Field(default_factory=ToolsAgentSettings)
    database: DatabaseAgentSettings = Field(default_factory=DatabaseAgentSettings)


# API keys (will be substituted from environment)
class APIKeys(BaseModel):
    anthropic: Optional[str] = None
    openai: Optional[str] = None
    openrouter: Optional[str] = None
    tavily: Optional[str] = None


# Configuration profiles
class ProfileSettings(BaseModel):
    master: Dict[str, Any] = Field(default_factory=dict)
    planner: Dict[str, Any] = Field(default_factory=dict)
    researcher: Dict[str, Any] = Field(default_factory=dict)
    tools: Dict[str, Any] = Field(default_factory=dict)
    database: Dict[str, Any] = Field(default_factory=dict)


class Profiles(BaseModel):
    fast: ProfileSettings = Field(
        default_factory=lambda: ProfileSettings(
            master={"model": "gpt-3.5-turbo"}, planner={"model": "gpt-3.5-turbo"}
        )
    )
    deep: ProfileSettings = Field(
        default_factory=lambda: ProfileSettings(
            master={"model": "claude-3-opus-20240229"},
            researcher={"max_urls_to_scrape": 10},
        )
    )


# Main configuration
class Config(BaseModel):
    version: str = "1.0"
    general: GeneralSettings = Field(default_factory=GeneralSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    agents: AgentsSettings = Field(default_factory=AgentsSettings)
    api_keys: APIKeys = Field(default_factory=APIKeys)
    profiles: Profiles = Field(default_factory=Profiles)
    rate_limiting: RateLimitingSettings = Field(default_factory=RateLimitingSettings)
    current_profile: Optional[str] = None


# Configuration update request
class ConfigUpdate(BaseModel):
    general: Optional[GeneralSettings] = None
    database: Optional[DatabaseSettings] = None
    agents: Optional[AgentsSettings] = None
    api_keys: Optional[APIKeys] = None
    profiles: Optional[Profiles] = None
    rate_limiting: Optional[RateLimitingSettings] = None


# Alias for backward compatibility
AppConfig = Config
